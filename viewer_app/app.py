from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import messagebox
from typing import Any

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .api_client import GatewayApiClient


BACKGROUND = "#f65f10"
PANEL = "#f7f3ed"
PANEL_EDGE = "#161616"
TEXT = "#1e1e1e"
GOOD = "#1a8a39"
WARN = "#b53b2d"


def build_api_url(host: str, port: str) -> str:
    host = host.strip() or "127.0.0.1"
    port = port.strip() or "4040"
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"http://{host}:{port}"


class ViewerApp(tk.Tk):
    def __init__(self, initial_url: str, poll_ms: int = 1000):
        super().__init__()
        self.title("CSI Gateway Viewer")
        self.geometry("1180x760")
        self.minsize(1040, 680)
        self.configure(bg=BACKGROUND)

        self.poll_ms = poll_ms
        self.client = GatewayApiClient(initial_url)
        self.latest_state: dict[str, Any] = {}

        self.host_var = tk.StringVar(value=self._initial_host(initial_url))
        self.port_var = tk.StringVar(value=self._initial_port(initial_url))
        self.status_var = tk.StringVar(value="Disconnected")
        self.total_nodes_var = tk.StringVar(value="Total Nodes: 0")
        self.endpoint_var = tk.StringVar(value=initial_url)

        self._build_ui()
        self.after(250, self.refresh_data)

    def _initial_host(self, url: str) -> str:
        without_scheme = url.replace("http://", "").replace("https://", "")
        host_part = without_scheme.split(":", 1)[0]
        return host_part or "127.0.0.1"

    def _initial_port(self, url: str) -> str:
        without_scheme = url.replace("http://", "").replace("https://", "")
        if ":" in without_scheme:
            return without_scheme.split(":", 1)[1].split("/", 1)[0]
        return "4040"

    def _build_ui(self):
        header = tk.Frame(self, bg=BACKGROUND)
        header.pack(fill="x", padx=18, pady=(14, 8))

        title_row = tk.Frame(header, bg=BACKGROUND)
        title_row.pack(fill="x")

        title = tk.Label(title_row, text="CSI Gateway Viewer", font=("Segoe UI Semibold", 22), fg=TEXT, bg=BACKGROUND)
        title.pack(side="left")

        total_nodes = tk.Label(title_row, textvariable=self.total_nodes_var, font=("Segoe UI", 13, "bold"), fg=TEXT, bg=BACKGROUND)
        total_nodes.pack(side="right")

        controls = tk.Frame(header, bg=BACKGROUND)
        controls.pack(fill="x", pady=(10, 0))

        tk.Label(controls, text="Host", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BACKGROUND).grid(row=0, column=0, sticky="w")
        tk.Entry(controls, textvariable=self.host_var, width=24, font=("Segoe UI", 10)).grid(row=1, column=0, padx=(0, 10), pady=(2, 0), sticky="we")
        tk.Label(controls, text="Port", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BACKGROUND).grid(row=0, column=1, sticky="w")
        tk.Entry(controls, textvariable=self.port_var, width=10, font=("Segoe UI", 10)).grid(row=1, column=1, padx=(0, 10), pady=(2, 0), sticky="w")

        tk.Button(controls, text="Connect", command=self.apply_connection, bg="#111111", fg="#ffffff", activebackground="#222222", activeforeground="#ffffff", relief="flat", padx=14, pady=5).grid(row=1, column=2, padx=(0, 8), pady=(2, 0))
        tk.Button(controls, text="Refresh", command=self.refresh_data, bg="#ffffff", fg=TEXT, activebackground="#f1f1f1", relief="flat", padx=14, pady=5).grid(row=1, column=3, pady=(2, 0))

        endpoint = tk.Label(controls, textvariable=self.endpoint_var, font=("Segoe UI", 9), fg=TEXT, bg=BACKGROUND)
        endpoint.grid(row=1, column=4, padx=(16, 0), sticky="w")

        controls.grid_columnconfigure(4, weight=1)

        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        self.canvas_panel = self._make_panel(body)
        self.canvas_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.canvas_panel.rowconfigure(0, weight=1)
        self.canvas_panel.columnconfigure(0, weight=1)

        right = tk.Frame(body, bg=BACKGROUND)
        right.pack(side="right", fill="y")

        self.info_panel = self._make_panel(right, width=410)
        self.info_panel.pack(fill="x")
        self.log_panel = self._make_panel(right, width=410)
        self.log_panel.pack(fill="both", expand=True, pady=(10, 0))

        self.figure = Figure(figsize=(6.5, 4.8), facecolor=PANEL)
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.figure_canvas = FigureCanvasTkAgg(self.figure, master=self.canvas_panel)
        self.figure_widget = self.figure_canvas.get_tk_widget()
        self.figure_widget.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self.figure_widget.configure(bg=PANEL, highlightthickness=0)
        self.figure.tight_layout(pad=1.2)

        info_header = tk.Label(self.info_panel, text="Node Information", font=("Segoe UI Semibold", 14), fg=TEXT, bg=PANEL)
        info_header.pack(anchor="w", padx=14, pady=(12, 6))

        self.info_text = tk.Text(self.info_panel, wrap="word", font=("Segoe UI", 10), bg=PANEL, fg=TEXT, relief="flat", bd=0, height=12)
        self.info_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.info_text.configure(state="disabled")

        log_header = tk.Label(self.log_panel, text="Log Viewer Output", font=("Segoe UI Semibold", 14), fg=TEXT, bg=PANEL)
        log_header.pack(anchor="w", padx=14, pady=(12, 6))

        self.log_text = tk.Text(self.log_panel, wrap="word", font=("Segoe UI", 10), bg=PANEL, fg=TEXT, relief="flat", bd=0)
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log_text.configure(state="disabled")

        footer = tk.Label(self, textvariable=self.status_var, bg=BACKGROUND, fg=TEXT, font=("Segoe UI", 10, "bold"))
        footer.pack(fill="x", padx=18, pady=(0, 12))

    def _make_panel(self, parent, width: int | None = None):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=2, highlightbackground=PANEL_EDGE, highlightcolor=PANEL_EDGE)
        if width is not None:
            frame.configure(width=width)
            frame.pack_propagate(False)
        return frame

    def apply_connection(self):
        url = build_api_url(self.host_var.get(), self.port_var.get())
        self.client = GatewayApiClient(url)
        self.endpoint_var.set(url)
        self.refresh_data()

    def refresh_data(self):
        try:
            self.latest_state = self.client.fetch_state()
            self.status_var.set(f"Connected to {self.client.base_url}")
            self.total_nodes_var.set(f"Total Nodes: {self.latest_state.get('total_nodes', 0)}")
            self._render_snapshot(self.latest_state)
        except Exception as exc:
            self.status_var.set(f"Unable to reach server: {exc}")
            self._render_offline()
        finally:
            self.after(self.poll_ms, self.refresh_data)

    def _render_offline(self):
        self._draw_offline_plot()
        self._set_text(self.info_text, "Connect to the API server to see node status and packet summaries.")
        self._set_text(self.log_text, "No packets received yet.")

    def _set_text(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def _render_snapshot(self, snapshot: dict[str, Any]):
        nodes = snapshot.get("nodes", []) or []
        self._draw_plot(nodes, snapshot)
        self._render_info(nodes, snapshot)
        self._render_logs(snapshot)

    def _draw_offline_plot(self):
        self._draw_plot([], {"latest_packet": None})

    def _draw_plot(self, nodes: list[dict[str, Any]], snapshot: dict[str, Any]):
        self.ax.clear()
        self.figure.set_facecolor(PANEL)
        self.ax.set_facecolor("#fbf7f1")

        self.ax.view_init(elev=24, azim=-58)
        self.ax.set_box_aspect((1.2, 1.0, 0.85))
        self.ax.dist = 9

        # Floor plane
        floor_x = [-3.2, 3.2, 3.2, -3.2]
        floor_y = [-3.2, -3.2, 3.2, 3.2]
        floor_z = [0, 0, 0, 0]
        self.ax.plot_trisurf(floor_x, floor_y, floor_z, color="#d8d8d8", alpha=0.55, linewidth=0.2, shade=False)

        # Axes lines
        self.ax.plot([-3.0, 3.0], [0, 0], [0, 0], color="#d62d2d", linewidth=3)
        self.ax.plot([0, 0], [-3.0, 3.0], [0, 0], color="#2e9c39", linewidth=3)
        self.ax.plot([0, 0], [0, 0], [0, 3.2], color="#2144d0", linewidth=3)

        self.ax.text(3.15, 0, 0, "X", color="#d62d2d", fontsize=10, fontweight="bold")
        self.ax.text(0, 3.15, 0, "Y", color="#2e9c39", fontsize=10, fontweight="bold")
        self.ax.text(0, 0, 3.35, "Z", color="#2144d0", fontsize=10, fontweight="bold")

        if nodes:
            xs = []
            ys = []
            zs = []
            sizes = []
            colors = []

            total = len(nodes)
            for index, node in enumerate(nodes):
                packet_rate = float(node.get("packet_rate") or 0.0)
                motion = float(node.get("motion") or 0.0)
                presence = bool(node.get("presence"))
                node_id = str(node.get("node_id") or f"node-{index + 1}")

                x = -2.2 + (index / max(total - 1, 1)) * 4.4
                y = max(min((packet_rate / 20.0) * 2.4 - 1.2, 2.2), -2.2)
                z = max(min(motion * 18.0, 2.8), 0.05)

                xs.append(x)
                ys.append(y)
                zs.append(z)
                sizes.append(70 + min(motion * 420.0, 260.0))
                colors.append(GOOD if presence else WARN)

                self.ax.text(x, y, z + 0.12, node_id, color=TEXT, fontsize=9, ha="center")

            self.ax.scatter(xs, ys, zs, s=sizes, c=colors, alpha=0.95, edgecolors="#111111", linewidths=0.8, depthshade=True)

        latest_packet = snapshot.get("latest_packet") or {}
        if latest_packet:
            label = (
                f"Latest: {latest_packet.get('node_id', 'unknown')}  "
                f"motion={float(latest_packet.get('motion') or 0.0):.3f}  "
                f"presence={bool(latest_packet.get('presence'))}"
            )
            self.ax.text2D(0.02, 0.95, label, transform=self.ax.transAxes, color=TEXT, fontsize=10, fontweight="bold")
        else:
            self.ax.text2D(0.02, 0.95, "Waiting for data feed...", transform=self.ax.transAxes, color=TEXT, fontsize=10, fontweight="bold")

        self.ax.set_xlim(-3.2, 3.2)
        self.ax.set_ylim(-3.2, 3.2)
        self.ax.set_zlim(0, 3.4)
        self.ax.set_xlabel("Lateral")
        self.ax.set_ylabel("Depth")
        self.ax.set_zlabel("Motion")
        self.ax.grid(False)

        for axis in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            axis.set_pane_color((1, 1, 1, 0))

        self.figure.tight_layout(pad=1.0)
        self.figure_canvas.draw_idle()

    def _render_info(self, nodes: list[dict[str, Any]], snapshot: dict[str, Any]):
        lines = []
        if not nodes:
            lines.append("No node data has been reported yet.")
        else:
            for node in nodes:
                lines.append(f"Node {node.get('node_id', 'unknown')} - {'Healthy' if node.get('presence') else 'Idle'}")
                lines.append(f"  packet rate: {float(node.get('packet_rate') or 0.0):.2f} packets/min")
                lines.append(f"  motion score: {float(node.get('motion') or 0.0):.4f}")
                lines.append(f"  rssi: {node.get('rssi')}")
                lines.append(f"  payload bytes: {node.get('payload_size')}")
                lines.append("")

        lines.append(f"Total packets: {snapshot.get('total_packets', 0)}")
        lines.append(f"Uptime: {snapshot.get('uptime_seconds', 0)}s")
        self._set_text(self.info_text, "\n".join(lines).strip())

    def _render_logs(self, snapshot: dict[str, Any]):
        recent = snapshot.get("recent_packets", []) or []
        if not recent:
            self._set_text(self.log_text, "Waiting for packets...\n")
            return

        lines = []
        for packet in recent[-12:]:
            node_id = packet.get("node_id", "unknown")
            motion = float(packet.get("motion") or 0.0)
            rate = float(packet.get("packet_rate") or 0.0)
            presence = "present" if packet.get("presence") else "quiet"
            lines.append(f"{node_id}: {presence}, motion={motion:.4f}, rate={rate:.2f}")

        self._set_text(self.log_text, "\n".join(lines))

    def _refresh_canvas(self):
        if self.latest_state:
            self._render_snapshot(self.latest_state)
        self.after(250, self._refresh_canvas)


def parse_args():
    parser = argparse.ArgumentParser(description="CSI Gateway Viewer")
    parser.add_argument("--api-url", default="http://127.0.0.1:4040", help="Base URL for the CSI Gateway API")
    parser.add_argument("--poll-ms", type=int, default=1000, help="Polling interval in milliseconds")
    return parser.parse_args()


def main():
    args = parse_args()
    app = ViewerApp(args.api_url, poll_ms=args.poll_ms)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        messagebox.showerror("CSI Gateway Viewer", str(exc))

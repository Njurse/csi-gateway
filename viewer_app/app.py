from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import messagebox
from typing import Any

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
        self.after(100, self._refresh_canvas)
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

        right = tk.Frame(body, bg=BACKGROUND)
        right.pack(side="right", fill="y")

        self.info_panel = self._make_panel(right, width=410)
        self.info_panel.pack(fill="x")
        self.log_panel = self._make_panel(right, width=410)
        self.log_panel.pack(fill="both", expand=True, pady=(10, 0))

        self.canvas = tk.Canvas(self.canvas_panel, bg=PANEL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=14, pady=14)

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
        self.canvas.delete("all")
        self.canvas.create_text(20, 20, anchor="nw", text="Waiting for data feed...", fill=TEXT, font=("Segoe UI", 12, "bold"))
        self._set_text(self.info_text, "Connect to the API server to see node status and packet summaries.")
        self._set_text(self.log_text, "No packets received yet.")

    def _set_text(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def _render_snapshot(self, snapshot: dict[str, Any]):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        self._draw_stage(width, height)

        nodes = snapshot.get("nodes", []) or []
        self._draw_nodes(nodes, width, height)
        self._render_info(nodes, snapshot)
        self._render_logs(snapshot)

    def _draw_stage(self, width: int, height: int):
        plane = [
            34, int(height * 0.66),
            int(width * 0.28), int(height * 0.50),
            int(width * 0.96), int(height * 0.61),
            int(width * 0.72), int(height * 0.79),
        ]
        self.canvas.create_polygon(*plane, fill="#cfcfcf", outline="#bebebe")
        self.canvas.create_line(int(width * 0.22), int(height * 0.72), int(width * 0.78), int(height * 0.72), fill="#d0d0d0", width=2)
        self.canvas.create_line(int(width * 0.34), int(height * 0.84), int(width * 0.34), int(height * 0.22), fill="#2144d0", width=3)
        self.canvas.create_line(int(width * 0.18), int(height * 0.72), int(width * 0.84), int(height * 0.84), fill="#d62d2d", width=3)
        self.canvas.create_line(int(width * 0.18), int(height * 0.72), int(width * 0.76), int(height * 0.50), fill="#2e9c39", width=3)
        self.canvas.create_text(int(width * 0.36), int(height * 0.17), text="3D signal plane", fill=TEXT, font=("Segoe UI", 11, "bold"))

    def _draw_nodes(self, nodes: list[dict[str, Any]], width: int, height: int):
        if not nodes:
            self.canvas.create_text(width // 2, height // 2, text="No nodes available yet", fill=TEXT, font=("Segoe UI", 13, "bold"))
            return

        total = len(nodes)
        for index, node in enumerate(nodes):
            packet_rate = float(node.get("packet_rate") or 0.0)
            motion = float(node.get("motion") or 0.0)
            presence = bool(node.get("presence"))
            node_id = str(node.get("node_id") or f"node-{index + 1}")

            normalized_rate = min(packet_rate / 20.0, 1.0)
            normalized_motion = min(motion / 0.25, 1.0)

            base_x = int(width * 0.24 + (index / max(total - 1, 1)) * width * 0.46)
            base_y = int(height * 0.70 - normalized_rate * height * 0.28 - normalized_motion * height * 0.12)
            radius = 10 + int(normalized_motion * 14)
            color = GOOD if presence else WARN

            self.canvas.create_oval(base_x - radius, base_y - radius, base_x + radius, base_y + radius, fill=color, outline="#0f0f0f", width=2)
            self.canvas.create_text(base_x, base_y - radius - 12, text=node_id, fill=TEXT, font=("Segoe UI", 10, "bold"))
            self.canvas.create_text(base_x, base_y + radius + 10, text=f"rate {packet_rate:.1f}  motion {motion:.3f}", fill=TEXT, font=("Segoe UI", 9))

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

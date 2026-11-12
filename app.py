import http.server
import socketserver
import os
import json
import base64
import io
import urllib.parse
import webbrowser
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from parser import parse_text_log, parse_dataframe_log
from visualizer import generate_topology_plot, ensure_icons

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class TopologyRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ['/', '/index.html']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(os.path.join(BASE_DIR, 'index.html'), 'rb') as f:
                self.wfile.write(f.read())
            return
        elif parsed.path == '/sample-log':
            sample_path = os.path.join(BASE_DIR, 'sample_router_log.txt')
            if os.path.exists(sample_path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                with open(sample_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_type = self.headers.get('Content-Type', '')
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        if parsed.path == '/api/generate-topology':
            try:
                ensure_icons()
                edges_df = pd.DataFrame()
                local_host = "Router"

                if 'multipart/form-data' in content_type:
                    boundary = content_type.split("boundary=")[-1].strip().encode('utf-8')
                    parts = post_data.split(b'--' + boundary)
                    for part in parts:
                        if b'filename=' in part:
                            subparts = part.split(b'\r\n\r\n', 1)
                            if len(subparts) == 2:
                                headers_part, file_bytes = subparts
                                file_bytes = file_bytes.rstrip(b'\r\n--')
                                header_str = headers_part.decode('utf-8', errors='ignore')

                                if '.xlsx' in header_str.lower() or '.xls' in header_str.lower():
                                    df = pd.read_excel(io.BytesIO(file_bytes))
                                    local_host, edges_df = parse_dataframe_log(df)
                                elif '.csv' in header_str.lower():
                                    df = pd.read_csv(io.BytesIO(file_bytes))
                                    local_host, edges_df = parse_dataframe_log(df)
                                else:
                                    text_data = file_bytes.decode('utf-8', errors='ignore')
                                    local_host, edges_df = parse_text_log(text_data)
                                break

                elif 'application/json' in content_type:
                    payload = json.loads(post_data.decode('utf-8'))
                    text_content = payload.get('text', '')
                    local_host, edges_df = parse_text_log(text_content)

                controller = generate_topology_plot(local_host, edges_df, return_controller=True)
                fig = controller.fig

                img_buf = io.BytesIO()
                fig.savefig(img_buf, format='png', dpi=130, facecolor=fig.get_facecolor(), edgecolor='none')
                plt.close(fig)
                img_buf.seek(0)
                b64_image = base64.b64encode(img_buf.read()).decode('utf-8')

                peer_list = edges_df.to_dict(orient='records') if not edges_df.empty else []
                response_data = {
                    'status': 'success',
                    'host': local_host,
                    'peer_count': len(peer_list),
                    'peers': peer_list,
                    'nodes': controller.nodes,
                    'core_nodes': controller.core_nodes,
                    'node_types': controller.node_types,
                    'positions': controller.positions,
                    'links': controller.links,
                    'image': f'data:image/png;base64,{b64_image}'
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
            return

        elif parsed.path == '/api/export-excel':
            try:
                payload = json.loads(post_data.decode('utf-8'))
                links = payload.get('links', [])
                node_types = payload.get('node_types', {})
                records = []
                for lk in links:
                    u = lk.get('u', '')
                    v = lk.get('v', '')
                    records.append({
                        'Source Device': u,
                        'Peer Device': v,
                        'Peer Type': node_types.get(v, 'router').capitalize(),
                        'Eth-Trunk / Interface': lk.get('label', '').replace('\n', ', '),
                        'Protocol / Service': lk.get('protocol', 'ISIS/MPLS TE')
                    })
                df_out = pd.DataFrame(records)
                excel_buf = io.BytesIO()
                df_out.to_excel(excel_buf, index=False, engine='openpyxl')
                excel_buf.seek(0)
                excel_bytes = excel_buf.read()

                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', 'attachment; filename="topology_links.xlsx"')
                self.send_header('Content-Length', str(len(excel_bytes)))
                self.end_headers()
                self.wfile.write(excel_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()


def run_app():
    ensure_icons()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), TopologyRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"Server listening on {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == '__main__':
    run_app()

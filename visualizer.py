import math
import re
import os
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import pandas as pd
from PIL import Image

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def ensure_icons():
    for fname in ('router.png', 'switch.png', 'firewall.png'):
        if not os.path.exists(os.path.join(ASSETS_DIR, fname)):
            import generate_assets
            generate_assets.generate_all_icons()
            break


def infer_device_type(node_name):
    n = node_name.lower()
    if any(k in n for k in ['switch', 'sw-', 'sw_', '-sw', '2960', '3850', '9300', 'nexus', 'ce68', 'ce88', 's57', 's67', 'l2']):
        return 'switch'
    if any(k in n for k in ['firewall', 'fw-', 'fw_', '-fw', 'asa', 'forti', 'palo', 'srx', 'usg', 'eudemon', 'sec']):
        return 'firewall'
    return 'router'


def get_device_icon(dev_type, size=(48, 48)):
    ensure_icons()
    dtype = dev_type.lower() if dev_type else 'router'
    if dtype not in ('router', 'switch', 'firewall'):
        dtype = 'router'
    cand = os.path.join(ASSETS_DIR, f'{dtype}.png')
    img = Image.open(cand).convert("RGBA")
    return img.resize(size, Image.Resampling.LANCZOS)


def get_pair_prefix(name):
    m = re.match(r'^(.+?)(?:[012]|A1|A2|B1|B2)$', name, re.I)
    return m.group(1) if m else name


def build_generic_topology_graph(local_node, edges_df):
    if edges_df is None or edges_df.empty:
        return [local_node], [], [local_node], {local_node: infer_device_type(local_node)}

    degree = defaultdict(int)
    adj = defaultdict(set)
    grouped_ports = defaultdict(list)
    protocols = defaultdict(set)

    all_nodes = []

    def add_node(n):
        if n and n not in all_nodes:
            all_nodes.append(n)

    add_node(local_node)

    for _, row in edges_df.iterrows():
        u = str(row.get('source', local_node)).strip()
        v = str(row.get('target', '')).strip()
        if not u or not v or u == v:
            continue
        add_node(u)
        add_node(v)

        sp = str(row.get('source_port', '') or '').strip()
        dp = str(row.get('target_port', '') or '').strip()
        proto = str(row.get('protocol', '') or '').strip()

        if sp.lower() == 'nan':
            sp = ''
        if dp.lower() == 'nan':
            dp = ''
        if proto.lower() == 'nan':
            proto = ''

        key = (u, v) if (u, v) in grouped_ports or (v, u) not in grouped_ports else (v, u)

        port_label = sp if sp else dp
        if port_label and port_label not in grouped_ports[key]:
            grouped_ports[key].append(port_label)
        if proto:
            protocols[key].add(proto)

        adj[u].add(v)
        adj[v].add(u)

    for n in all_nodes:
        degree[n] = len(adj[n])

    sorted_by_deg = sorted(all_nodes, key=lambda x: (degree[x], x == local_node), reverse=True)
    primary_core = sorted_by_deg[0] if sorted_by_deg else local_node
    core_nodes = [primary_core]

    if len(sorted_by_deg) > 1:
        second_cand = sorted_by_deg[1]
        if degree[second_cand] >= 2:
            core_nodes.append(second_cand)
        else:
            core_prefix = get_pair_prefix(primary_core)
            for nbr in adj[primary_core]:
                if get_pair_prefix(nbr) == core_prefix and nbr != primary_core:
                    core_nodes.append(nbr)
                    break

    links = []
    for (u, v), port_list in grouped_ports.items():
        lbl = "\n".join(port_list[:3]) if port_list else ""
        proto_str = ", ".join(sorted(protocols[(u, v)]))
        is_second_core = (len(core_nodes) > 1 and (u == core_nodes[1] or v == core_nodes[1]) and not (u == core_nodes[0] or v == core_nodes[0]))
        color = '#2563eb' if is_second_core else '#1e293b'
        links.append({
            'u': u,
            'v': v,
            'label': lbl,
            'protocol': proto_str or 'ISIS/MPLS TE',
            'color': color,
            'label_t': 0.55,
            'offset_x': 0.0,
            'offset_y': 0.0
        })

    existing_pairs = {tuple(sorted((l['u'], l['v']))) for l in links}
    peripherals = [n for n in all_nodes if n not in core_nodes]
    by_prefix = defaultdict(list)
    for p in peripherals:
        by_prefix[get_pair_prefix(p)].append(p)
    for _, group in by_prefix.items():
        if len(group) == 2:
            pair_k = tuple(sorted((group[0], group[1])))
            if pair_k not in existing_pairs:
                links.append({
                    'u': group[0],
                    'v': group[1],
                    'label': '',
                    'protocol': 'Peer-Link',
                    'color': '#475569',
                    'label_t': 0.5,
                    'offset_x': 0.0,
                    'offset_y': 0.0
                })
                existing_pairs.add(pair_k)

    node_types = {n: infer_device_type(n) for n in all_nodes}
    return all_nodes, links, core_nodes, node_types


def compute_generic_layout(all_nodes, links, core_nodes):
    positions = {}
    if not all_nodes:
        return positions

    if len(core_nodes) == 1:
        positions[core_nodes[0]] = (50.0, 55.0)
    elif len(core_nodes) >= 2:
        positions[core_nodes[0]] = (41.0, 56.0)
        positions[core_nodes[1]] = (59.0, 56.0)
        for idx, extra_core in enumerate(core_nodes[2:]):
            positions[extra_core] = (50.0 + (idx - 0.5) * 18.0, 72.0)

    peripherals = [n for n in all_nodes if n not in positions]
    if not peripherals:
        return positions

    prefix_groups = defaultdict(list)
    for p in peripherals:
        prefix_groups[get_pair_prefix(p)].append(p)

    ordered_groups = list(prefix_groups.values())
    ordered_peripherals = [node for grp in ordered_groups for node in grp]
    total_p = len(ordered_peripherals)

    if total_p <= 6:
        top_count = total_p // 2
        top_nodes = ordered_peripherals[:top_count]
        bot_nodes = ordered_peripherals[top_count:]

        for i, n in enumerate(top_nodes):
            x = 50.0 if len(top_nodes) == 1 else 25.0 + i * (50.0 / (len(top_nodes) - 1))
            positions[n] = (x, 86.0)

        for i, n in enumerate(bot_nodes):
            x = 50.0 if len(bot_nodes) == 1 else 20.0 + i * (60.0 / (len(bot_nodes) - 1))
            positions[n] = (x, 16.0)
        return positions

    top_count = min(4, max(2, (total_p // 4) * 2))
    rem = total_p - top_count
    left_count = 2 if rem >= 6 else 0
    right_count = 2 if rem >= 8 else 0

    idx = 0
    top_nodes = ordered_peripherals[idx:idx + top_count]
    idx += top_count
    left_nodes = ordered_peripherals[idx:idx + left_count]
    idx += left_count
    right_nodes = ordered_peripherals[idx:idx + right_count]
    idx += right_count
    bot_nodes = ordered_peripherals[idx:]

    for i, n in enumerate(top_nodes):
        x = 50.0 if len(top_nodes) == 1 else 22.0 + i * (56.0 / (len(top_nodes) - 1))
        positions[n] = (x, 88.0)

    for i, n in enumerate(left_nodes):
        positions[n] = (9.0, 38.0 - i * 13.0)

    for i, n in enumerate(right_nodes):
        positions[n] = (91.0, 38.0 - i * 13.0)

    for i, n in enumerate(bot_nodes):
        x = 50.0 if len(bot_nodes) == 1 else 10.0 + i * (80.0 / (len(bot_nodes) - 1))
        positions[n] = (x, 12.0)

    return positions


class InteractiveTopologyCanvas:
    def __init__(self, local_node, edges_df, figsize=(13.5, 8.8), on_edit_node=None, on_edit_link=None):
        self.local_node = local_node
        self.edges_df = edges_df if edges_df is not None else pd.DataFrame()
        self.nodes, self.links, self.core_nodes, self.node_types = build_generic_topology_graph(local_node, self.edges_df)
        self.positions = compute_generic_layout(self.nodes, self.links, self.core_nodes)
        self.core_banner = "ISIS/MPLS TE,\nLDP/BGP"

        self.on_edit_node = on_edit_node
        self.on_edit_link = on_edit_link

        self.fig, self.ax = plt.subplots(figsize=figsize, dpi=120)
        self.dragging_node = None
        self.dragging_link_idx = None
        self.drag_start_mouse = (0, 0)
        self.drag_start_pos = (0, 0)
        self._cids = []

        for idx, lk in enumerate(self.links):
            u, v = lk['u'], lk['v']
            if u in self.core_nodes and v in self.core_nodes:
                lk['label_t'] = 0.5
                lk['offset_y'] = 2.2
            else:
                lk['label_t'] = 0.54 + (idx % 3) * 0.09

        self.draw_canvas()
        self.connect_events()

    def connect_events(self):
        for cid in self._cids:
            try:
                self.fig.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._cids = [
            self.fig.canvas.mpl_connect('button_press_event', self.on_press),
            self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion),
            self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        ]

    def get_link_label_coords(self, lk):
        u, v = lk['u'], lk['v']
        x1, y1 = self.positions.get(u, (50, 50))
        x2, y2 = self.positions.get(v, (50, 50))
        t = lk.get('label_t', 0.55)
        lx = x1 + (x2 - x1) * t + lk.get('offset_x', 0.0)
        ly = y1 + (y2 - y1) * t + lk.get('offset_y', 0.0)
        return lx, ly

    def find_hit_target(self, mx, my):
        best_node = None
        best_dist = 4.8
        for n, (nx, ny) in self.positions.items():
            d = math.hypot(mx - nx, my - ny)
            if d < best_dist:
                best_dist = d
                best_node = n
        if best_node is not None:
            return ('node', best_node)

        best_link_idx = None
        best_l_dist = 4.8
        for idx, lk in enumerate(self.links):
            lx, ly = self.get_link_label_coords(lk)
            d = math.hypot(mx - lx, my - ly)
            if d < best_l_dist:
                best_l_dist = d
                best_link_idx = idx
        if best_link_idx is not None:
            return ('link', best_link_idx)

        return (None, None)

    def on_press(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        mx, my = event.xdata, event.ydata
        hit_type, hit_val = self.find_hit_target(mx, my)

        if event.dblclick or event.button == 3:
            if hit_type == 'node' and self.on_edit_node:
                self.on_edit_node(hit_val)
                return
            if hit_type == 'link' and self.on_edit_link:
                self.on_edit_link(hit_val)
                return

        if event.button == 1:
            if hit_type == 'node':
                self.dragging_node = hit_val
                self.drag_start_mouse = (mx, my)
                self.drag_start_pos = self.positions[hit_val]
            elif hit_type == 'link':
                self.dragging_link_idx = hit_val
                self.drag_start_mouse = (mx, my)
                lk = self.links[hit_val]
                self.drag_start_pos = (lk.get('offset_x', 0.0), lk.get('offset_y', 0.0))

    def on_motion(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        mx, my = event.xdata, event.ydata

        if self.dragging_node is not None:
            dx = mx - self.drag_start_mouse[0]
            dy = my - self.drag_start_mouse[1]
            nx = max(4.0, min(96.0, self.drag_start_pos[0] + dx))
            ny = max(6.0, min(94.0, self.drag_start_pos[1] + dy))
            self.positions[self.dragging_node] = (nx, ny)
            self.draw_canvas()
            self.fig.canvas.draw_idle()

        elif self.dragging_link_idx is not None:
            dx = mx - self.drag_start_mouse[0]
            dy = my - self.drag_start_mouse[1]
            lk = self.links[self.dragging_link_idx]
            lk['offset_x'] = self.drag_start_pos[0] + dx
            lk['offset_y'] = self.drag_start_pos[1] + dy
            self.draw_canvas()
            self.fig.canvas.draw_idle()

    def on_release(self, event):
        self.dragging_node = None
        self.dragging_link_idx = None

    def rename_and_update_node(self, old_name, new_name, new_type, is_core=None):
        new_name = new_name.strip() or old_name
        if new_name != old_name:
            self.nodes = [new_name if n == old_name else n for n in self.nodes]
            self.core_nodes = [new_name if n == old_name else n for n in self.core_nodes]
            if old_name in self.positions:
                self.positions[new_name] = self.positions.pop(old_name)
            if old_name in self.node_types:
                self.node_types.pop(old_name)
            for lk in self.links:
                if lk['u'] == old_name:
                    lk['u'] = new_name
                if lk['v'] == old_name:
                    lk['v'] = new_name
            if self.local_node == old_name:
                self.local_node = new_name

        self.node_types[new_name] = new_type.lower()
        if is_core is not None:
            if is_core and new_name not in self.core_nodes:
                self.core_nodes.append(new_name)
            elif not is_core and new_name in self.core_nodes:
                self.core_nodes.remove(new_name)

        self.draw_canvas()
        self.fig.canvas.draw_idle()

    def update_link_info(self, link_idx, new_label, new_protocol=None, new_color=None):
        if 0 <= link_idx < len(self.links):
            self.links[link_idx]['label'] = new_label
            if new_protocol is not None:
                self.links[link_idx]['protocol'] = new_protocol
            if new_color is not None:
                self.links[link_idx]['color'] = new_color
            self.draw_canvas()
            self.fig.canvas.draw_idle()

    def reset_layout(self):
        self.positions = compute_generic_layout(self.nodes, self.links, self.core_nodes)
        for lk in self.links:
            lk['offset_x'] = 0.0
            lk['offset_y'] = 2.2 if (lk['u'] in self.core_nodes and lk['v'] in self.core_nodes) else 0.0
        self.draw_canvas()
        self.fig.canvas.draw_idle()

    def draw_canvas(self):
        ax = self.ax
        ax.clear()

        bg_color = '#ffffff'
        self.fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_xticks(range(0, 101, 2))
        ax.set_yticks(range(0, 101, 2))
        ax.grid(True, which='both', color='#e2e8f0', linestyle='-', linewidth=0.55, alpha=0.9, zorder=0)
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.tick_params(left=False, bottom=False)

        for c_node in self.core_nodes[:2]:
            if c_node in self.positions:
                cx, cy = self.positions[c_node]
                rect = Rectangle((cx - 3.6, cy - 4.2), 7.2, 8.4, linewidth=1.8, edgecolor='#ef4444', facecolor='none', zorder=4)
                ax.add_patch(rect)

        if len(self.core_nodes) >= 2 and self.core_nodes[0] in self.positions and self.core_nodes[1] in self.positions:
            c1x, c1y = self.positions[self.core_nodes[0]]
            c2x, c2y = self.positions[self.core_nodes[1]]
            mid_x, mid_y = (c1x + c2x) / 2.0, (c1y + c2y) / 2.0 + 5.8
            ax.text(mid_x, mid_y, self.core_banner, fontsize=8.5, fontweight='bold', color='#0f172a', ha='center', va='center', zorder=7)

        for lk in self.links:
            u, v = lk['u'], lk['v']
            if u not in self.positions or v not in self.positions:
                continue
            x1, y1 = self.positions[u]
            x2, y2 = self.positions[v]
            col = lk.get('color', '#1e293b')

            ax.plot([x1, x2], [y1, y2], color=col, linewidth=1.35, alpha=0.88, zorder=2)

            lbl = lk.get('label', '')
            if lbl:
                lx, ly = self.get_link_label_coords(lk)
                ax.text(
                    lx, ly, lbl, color=col, fontsize=6.5, fontweight='bold',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.18', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.92, linewidth=0.6),
                    zorder=6
                )

        type_color_map = {
            'router': '#b45309',
            'switch': '#1d4ed8',
            'firewall': '#b91c1c'
        }
        for name, (x, y) in self.positions.items():
            is_core = name in self.core_nodes[:2]
            dtype = self.node_types.get(name, 'router')
            icon_img = get_device_icon(dtype, size=(48, 48))
            ib = OffsetImage(icon_img, zoom=0.66 if is_core else 0.56)
            ab = AnnotationBbox(ib, (x, y), frameon=False, zorder=8)
            ax.add_artist(ab)

            lbl_color = '#0f172a' if dtype == 'router' else type_color_map.get(dtype, '#0f172a')

            if is_core and len(self.core_nodes) >= 2 and self.core_nodes[0] in self.positions and self.core_nodes[1] in self.positions:
                c1_x = self.positions[self.core_nodes[0]][0]
                c2_x = self.positions[self.core_nodes[1]][0]
                if name == self.core_nodes[0] and c1_x <= c2_x:
                    ax.text(x - 4.5, y, name, color=lbl_color, fontsize=8, fontweight='bold', ha='right', va='center', zorder=9)
                elif name == self.core_nodes[1] and c2_x >= c1_x:
                    ax.text(x + 4.5, y, name, color=lbl_color, fontsize=8, fontweight='bold', ha='left', va='center', zorder=9)
                else:
                    ax.text(x, y + 5.2, name, color=lbl_color, fontsize=8, fontweight='bold', ha='center', va='bottom', zorder=9)
            else:
                lbl_y = y + 4.0 if y > 55 else y - 4.0
                va = 'bottom' if y > 55 else 'top'
                ax.text(x, lbl_y, name, color=lbl_color, fontsize=7.2, fontweight='bold', ha='center', va=va, zorder=9)

        self.fig.tight_layout()


def generate_topology_plot(local_node, edges_df, output_path=None, figsize=(13.5, 8.8), return_controller=False, on_edit_node=None, on_edit_link=None):
    controller = InteractiveTopologyCanvas(local_node, edges_df, figsize=figsize, on_edit_node=on_edit_node, on_edit_link=on_edit_link)
    if output_path:
        controller.fig.savefig(output_path, dpi=160, facecolor=controller.fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
        with Image.open(output_path) as im:
            im.verify()
    if return_controller:
        return controller
    return controller.fig

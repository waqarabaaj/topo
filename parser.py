import re
import os
import pandas as pd


def parse_router_logs(file_path_or_text, is_file=True):
    if is_file:
        ext = os.path.splitext(file_path_or_text)[1].lower()
        if ext in ['.xlsx', '.xls']:
            return parse_excel_log(file_path_or_text)
        elif ext == '.csv':
            return parse_csv_log(file_path_or_text)
        with open(file_path_or_text, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    else:
        content = file_path_or_text

    return parse_text_log(content)


def parse_excel_log(file_path):
    df = pd.read_excel(file_path)
    return parse_dataframe_log(df)


def parse_csv_log(file_path):
    df = pd.read_csv(file_path)
    return parse_dataframe_log(df)


def parse_dataframe_log(df):
    cols = {str(c).strip().lower(): c for c in df.columns}

    src_col = next((cols[c] for c in cols if any(k in c for k in ['source', 'local_dev', 'local device', 'device', 'router', 'host', 'from', 'node_a', 'node1'])), None)
    dst_col = next((cols[c] for c in cols if any(k in c for k in ['target', 'neighbor', 'peer', 'remote', 'to', 'node_b', 'node2', 'dest'])), None)
    trunk_col = next((cols[c] for c in cols if any(k in c for k in ['trunk', 'interface', 'eth-trunk', 'port', 'link', 'local_int'])), None)
    remote_port_col = next((cols[c] for c in cols if any(k in c for k in ['remote_port', 'remote_int', 'peer_port', 'target_port']) and cols[c] != trunk_col), None)
    capacity_col = next((cols[c] for c in cols if any(k in c for k in ['bandwidth', 'capacity', 'speed', 'rate', 'bw'])), None)
    proto_col = next((cols[c] for c in cols if any(k in c for k in ['proto', 'type', 'service'])), None)

    records = []
    local_node = "Core-Router"

    if not dst_col and len(df.columns) >= 2:
        src_col = df.columns[0]
        dst_col = df.columns[1]
        if len(df.columns) >= 3:
            trunk_col = df.columns[2]

    if dst_col:
        first_src = None
        for _, row in df.iterrows():
            s = str(row[src_col]).strip() if src_col and pd.notna(row[src_col]) else local_node
            t = str(row[dst_col]).strip() if pd.notna(row[dst_col]) else None
            if not t or t.lower() in ['nan', 'none', '']:
                continue
            if not first_src and s:
                first_src = s

            trunk = str(row[trunk_col]).strip() if trunk_col and pd.notna(row[trunk_col]) else ""
            if trunk.lower() == 'nan':
                trunk = ""
            r_port = str(row[remote_port_col]).strip() if remote_port_col and pd.notna(row[remote_port_col]) else ""
            if r_port.lower() == 'nan':
                r_port = ""
            cap = str(row[capacity_col]).strip() if capacity_col and pd.notna(row[capacity_col]) else ""
            if cap.lower() == 'nan':
                cap = ""
            if cap and '(' not in trunk:
                trunk = f"{trunk}({cap})" if trunk else cap

            proto = str(row[proto_col]).strip() if proto_col and pd.notna(row[proto_col]) else ""
            if proto.lower() == 'nan':
                proto = ""

            records.append({
                'source': s,
                'target': t,
                'source_port': trunk,
                'target_port': r_port,
                'protocol': proto
            })
        if first_src:
            local_node = first_src

    return local_node, pd.DataFrame(records)


def is_valid_device_name(name):
    if not name or len(name) < 2:
        return False
    if all(c in '-=_*#<>.:/\\ ' for c in name):
        return False
    ignore = {
        'huawei', 'cisco', 'juniper', 'system', 'line', 'user', 'enable', 'config',
        'interface', 'display', 'show', 'description', 'current', 'state', 'up', 'down',
        'protocol', 'ip', 'address', 'eth-trunk', 'port', 'neighbor', 'device', 'id',
        'local', 'holdtme', 'capability', 'platform', 'total', 'entries', 'displayed',
        'the', 'is', 'to', 'from', 'on', 'with', 'full', 'loading', 'established'
    }
    return name.lower() not in ignore


def format_trunk_name(raw_intf, capacity=""):
    raw_intf = raw_intf.strip()
    m = re.match(r'^Eth-Trunk\s*(\d+)(.*)$', raw_intf, re.I)
    if m:
        num, rest = m.group(1), m.group(2).strip()
        base = f"Eth-Trunk {num}"
        if rest:
            base += rest
        if capacity and '(' not in base:
            base += f"({capacity})"
        return base
    if capacity and '(' not in raw_intf:
        return f"{raw_intf}({capacity})"
    return raw_intf


def parse_text_log(content):
    current_host = "Router-1"
    first_detected_host = None

    for line in content.splitlines():
        line_s = line.strip()
        m_prompt = re.match(r'^[<\[]([A-Za-z0-9_\-\.]+)[>\]]', line_s)
        if not m_prompt:
            m_prompt = re.match(r'^([A-Za-z0-9_\-\.]+)[#>]', line_s)
        if not m_prompt:
            m_prompt = re.search(r'^\s*(?:sysname|hostname)\s+([A-Za-z0-9_\-\.]+)', line_s, re.I)
        if m_prompt:
            cand = m_prompt.group(1).strip()
            if is_valid_device_name(cand):
                current_host = cand
                first_detected_host = cand
                break

    edges = []
    lines = content.splitlines()
    active_interface = ""
    active_bw = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        m_p = re.match(r'^[<\[]([A-Za-z0-9_\-\.]+)[>\]]', line)
        if not m_p:
            m_p = re.match(r'^([A-Za-z0-9_\-\.]+)[#>]\s*(?:show|display|dir|ping|tracert|quit|exit|)', line, re.I)
        if m_p:
            cand = m_p.group(1).strip()
            if is_valid_device_name(cand):
                current_host = cand
                if not first_detected_host:
                    first_detected_host = cand

        m_sys = re.match(r'^(?:sysname|hostname)\s+([A-Za-z0-9_\-\.]+)', line, re.I)
        if m_sys:
            cand = m_sys.group(1).strip()
            if is_valid_device_name(cand):
                current_host = cand
                if not first_detected_host:
                    first_detected_host = cand
                continue

        m_eth_peer = re.search(
            r'((?:Eth-Trunk|Port-channel|Bundle-Ether|GigabitEthernet|TenGigE|100GE|40GE|25GE|10GE|GE|Gi|Te|Eth)\s*[\d\/\.\:]+(?:\s*\([\d\w]+\))?)'
            r'.*?(?:Peer|Neighbor|to|TO|-->|<-->|Remote)\s*[:\-]?\s*([A-Za-z0-9_\-\.]+)'
            r'(?:.*?\((\d+\s*[GMK]b?p?s?|\d+[GMK])\))?',
            line, re.I
        )
        if m_eth_peer:
            intf_raw = m_eth_peer.group(1).strip()
            peer_dev = m_eth_peer.group(2).strip()
            cap = m_eth_peer.group(3).strip() if m_eth_peer.group(3) else ""
            if is_valid_device_name(peer_dev):
                edges.append({
                    'source': current_host,
                    'target': peer_dev,
                    'source_port': format_trunk_name(intf_raw, cap),
                    'target_port': '',
                    'protocol': 'Eth-Trunk' if 'trunk' in intf_raw.lower() else 'Link'
                })
                continue

        m_intf_ctx = re.match(
            r'^(?:interface\s+)?((?:Eth-Trunk|Port-channel|Bundle-Ether|100GE|40GE|25GE|10GE|GigabitEthernet|TenGigE|GE)\s*[\d\/\.\:]+)(?:\s+current\s+state|\s*$)',
            line, re.I
        )
        if m_intf_ctx:
            active_interface = m_intf_ctx.group(1).strip()
            bw_search = re.search(r'(\d+\s*[GMK]bps|\d+[GMK])', line, re.I)
            active_bw = bw_search.group(1) if bw_search else ""

        if active_interface:
            m_bw = re.search(r'(?:Current BW|Bandwidth|Speed)\s*:\s*(\d+\s*[GMK]b?p?s?|\d+[GMK])', line, re.I)
            if m_bw:
                active_bw = m_bw.group(1).strip()

            m_desc = re.search(r'^description\s*:?\s*(.+)$', line, re.I)
            if m_desc:
                desc_text = m_desc.group(1).strip()
                m_peer_in_desc = re.search(
                    r'(?:to|peer|nbr|conn)?[\s_\-:]*([A-Za-z0-9]+(?:-[A-Za-z0-9]+){1,6})(?:[\s_\-:]+((?:Eth-Trunk|Port-channel|Gi|Te|100GE|40GE|10GE|GE)[\d\/\.\s]*(?:\([\d\w]+\))?))?(?:.*?\((\d+[GMK])\))?',
                    desc_text, re.I
                )
                if m_peer_in_desc:
                    peer_cand = m_peer_in_desc.group(1).strip()
                    rem_intf = m_peer_in_desc.group(2).strip() if m_peer_in_desc.group(2) else ""
                    cap = m_peer_in_desc.group(3) or active_bw
                    if is_valid_device_name(peer_cand):
                        edges.append({
                            'source': current_host,
                            'target': peer_cand,
                            'source_port': format_trunk_name(active_interface, cap),
                            'target_port': rem_intf,
                            'protocol': 'Eth-Trunk' if 'trunk' in active_interface.lower() else 'Physical'
                        })
                        continue

        m_huawei_lldp = re.match(
            r'^((?:Eth-Trunk|100GE|40GE|25GE|10GE|GE|XGE|GigabitEthernet|TenGigE|Gi|Te|Eth)[\d\/\.\:]+)\s+([A-Za-z0-9_\-\.]+)\s+([A-Za-z0-9\/\.\:\-]+)\s+\d+\s*$',
            line, re.I
        )
        if m_huawei_lldp:
            loc_i, peer_d, rem_i = m_huawei_lldp.group(1), m_huawei_lldp.group(2), m_huawei_lldp.group(3)
            if is_valid_device_name(peer_d):
                edges.append({
                    'source': current_host,
                    'target': peer_d,
                    'source_port': format_trunk_name(loc_i),
                    'target_port': rem_i,
                    'protocol': 'LLDP'
                })
                continue

        m_cisco_cdp = re.match(
            r'^([A-Za-z0-9_\-\.]+)\s+((?:Gig|TenGig|Eth|Fa|Po|Eth-Trunk|Gi|Te)\s*[\d\/\.\:]+)\s+\d+\s+[A-Za-z\s]+?\s{2,}[A-Za-z0-9_\-\.]+\s+((?:Gig|TenGig|Eth|Fa|Po|Gi|Te)\s*[\d\/\.\:]+|[A-Za-z0-9\/\.\:]+)',
            line, re.I
        )
        if m_cisco_cdp:
            peer_d, loc_i, rem_i = m_cisco_cdp.group(1), m_cisco_cdp.group(2), m_cisco_cdp.group(3)
            if is_valid_device_name(peer_d):
                edges.append({
                    'source': current_host,
                    'target': peer_d,
                    'source_port': loc_i.strip(),
                    'target_port': rem_i.strip(),
                    'protocol': 'CDP/LLDP'
                })
                continue

        m_isis = re.match(
            r'^([A-Za-z0-9_\-\.]+)\s+((?:Eth-Trunk|100GE|40GE|25GE|10GE|GE|XGE|Gi|Te|Po|Vlanif|LoopBack)[\d\/\.\:]+(?:\([\d\w]+\))?)\s+\S+\s+(Up|Init|Down)\s+\d+',
            line, re.I
        )
        if m_isis:
            peer_d, loc_i, state = m_isis.group(1), m_isis.group(2), m_isis.group(3)
            if is_valid_device_name(peer_d):
                edges.append({
                    'source': current_host,
                    'target': peer_d,
                    'source_port': format_trunk_name(loc_i),
                    'target_port': '',
                    'protocol': f'ISIS ({state})'
                })
                continue

        m_ospf = re.match(
            r'^(\d{1,3}(?:\.\d{1,3}){3})\s+\d+\s+(FULL[A-Za-z\/\-]*|2WAY[A-Za-z\/\-]*)\s+[\d\:]+\s+(\d{1,3}(?:\.\d{1,3}){3})\s+([A-Za-z0-9\/\.\:\-]+)',
            line, re.I
        )
        if m_ospf:
            nbr_id, state, ip_addr, intf = m_ospf.group(1), m_ospf.group(2), m_ospf.group(3), m_ospf.group(4)
            edges.append({
                'source': current_host,
                'target': f"OSPF-{nbr_id}",
                'source_port': format_trunk_name(intf),
                'target_port': ip_addr,
                'protocol': f"OSPF ({state})"
            })
            continue

        m_generic_link = re.match(
            r'^([A-Za-z0-9_\-\.]+)\s*(?:<-->|-->|<->|->|—|--)\s*([A-Za-z0-9_\-\.]+)(?:\s*[:\|,]?\s*(.+))?$',
            line
        )
        if m_generic_link:
            s, t, rest = m_generic_link.group(1).strip(), m_generic_link.group(2).strip(), (m_generic_link.group(3) or '').strip()
            if is_valid_device_name(s) and is_valid_device_name(t):
                edges.append({
                    'source': s,
                    'target': t,
                    'source_port': format_trunk_name(rest) if rest else 'Eth-Trunk',
                    'target_port': '',
                    'protocol': 'ISIS/MPLS TE'
                })
                if not first_detected_host:
                    first_detected_host = s
                continue

    detail_blocks = re.split(r'-{10,}|={10,}', content)
    for block in detail_blocks:
        dev_m = re.search(r'(?:Device ID|System Name|Neighbor Dev|SysName)\s*:\s*([A-Za-z0-9_\-\.]+)', block, re.I)
        intf_m = re.search(r'(?:Local Interface|Local Intf|Interface)\s*:\s*([A-Za-z0-9\/\.\-\s]+)', block, re.I)
        port_m = re.search(r'(?:Port ID(?:\s*\(outgoing port\))?|Neighbor Intf)\s*:\s*([A-Za-z0-9\/\.\-\s]+)', block, re.I)
        if dev_m:
            target = dev_m.group(1).strip()
            if is_valid_device_name(target):
                sp = intf_m.group(1).strip() if intf_m else ""
                dp = port_m.group(1).strip() if port_m else ""
                edges.append({
                    'source': first_detected_host or current_host,
                    'target': target,
                    'source_port': format_trunk_name(sp),
                    'target_port': dp,
                    'protocol': 'LLDP/CDP'
                })

    df = pd.DataFrame(edges)
    if not df.empty:
        df = df.drop_duplicates(subset=['source', 'target', 'source_port', 'target_port'])

    return (first_detected_host or current_host), df

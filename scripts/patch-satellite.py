#!/usr/bin/env python3
"""Patches surface-entrypoint.mjs with correct NEP logo scaling and info display."""

import sys, shutil, re

TARGET = '/opt/companion-satellite/satellite/dist/surface-entrypoint.mjs'

try:
    with open(TARGET, 'r') as f:
        src = f.read()
except FileNotFoundError:
    print(f'FEIL: {TARGET} ikke funnet')
    sys.exit(1)

# Read NEP_ID from nep-health service
nep_id = 'Satellite Pi'
try:
    with open('/etc/systemd/system/nep-health.service') as f:
        for line in f:
            m = re.search(r'Environment="?NEP_ID=([^"\n]+)"?', line)
            if m:
                nep_id = m.group(1).strip()
                break
except Exception:
    pass

print(f'  Pi-ID: {nep_id}')

# Crop coordinates: content area of 2000x1126 logo (wheel + 40 mark)
SRC_X, SRC_Y, SRC_W, SRC_H = 60, 80, 1700, 980

OLD_BASIC = '''    const iconTargetSize = Math.round(Math.min(width, height) * 0.6);
    const iconTargetX = (width - iconTargetSize) / 2;
    const iconTargetY = (height - iconTargetSize) / 2;
    context2d.drawImage(
      iconImage,
      0,
      0,
      iconImage.width,
      iconImage.height,
      iconTargetX,
      iconTargetY,
      iconTargetSize,
      iconTargetSize
    );
    context2d.font = `normal normal normal ${12}px sans-serif`;
    context2d.textAlign = "left";
    context2d.fillStyle = "#ffffff";
    context2d.fillText(`Remote: ${remoteIp}`, 10, height - 10);
    context2d.fillText(`Local: ${getIPAddress()}`, 10, height - 30);
    context2d.fillText(`Status: ${status}`, 10, height - 50);'''

NEW_BASIC = f'''    const _sx={SRC_X},_sy={SRC_Y},_sw={SRC_W},_sh={SRC_H};
    const _lh=Math.floor(height*0.50),_m=4;
    const _sc=Math.min((width-_m*2)/_sw,(_lh-4)/_sh);
    const _dw=Math.max(1,Math.floor(_sw*_sc)),_dh=Math.max(1,Math.floor(_sh*_sc));
    context2d.drawImage(iconImage,_sx,_sy,_sw,_sh,Math.floor((width-_dw)/2),Math.floor((_lh-_dh)/2),_dw,_dh);
    context2d.textAlign="left";
    let _y=_lh+13;
    context2d.font="bold 12px sans-serif";
    context2d.fillStyle=status==="Connected"?"#00cc44":"#ff8800";
    context2d.fillText(status,4,_y);_y+=13;
    context2d.font="11px sans-serif";
    context2d.fillStyle="#dddddd";
    context2d.fillText("IP: "+getIPAddress(),4,_y);_y+=12;
    context2d.fillStyle="#aaaaaa";
    context2d.fillText("{nep_id}",4,_y);'''

OLD_LOGO = '''    const iconTargetSize = Math.round(Math.min(width, height) * 0.8);
    const iconTargetX = (width - iconTargetSize) / 2;
    const iconTargetY = (height - iconTargetSize) / 2;
    context2d.drawImage(
      iconImage,
      0,
      0,
      iconImage.width,
      iconImage.height,
      iconTargetX,
      iconTargetY,
      iconTargetSize,
      iconTargetSize
    );'''

NEW_LOGO = f'''    const _lsx={SRC_X},_lsy={SRC_Y},_lsw={SRC_W},_lsh={SRC_H};
    const _lsc=Math.min((width-6)/_lsw,(height-6)/_lsh);
    const _ldw=Math.max(1,Math.floor(_lsw*_lsc)),_ldh=Math.max(1,Math.floor(_lsh*_lsc));
    context2d.drawImage(iconImage,_lsx,_lsy,_lsw,_lsh,Math.floor((width-_ldw)/2),Math.floor((height-_ldh)/2),_ldw,_ldh);'''

changed = False

if OLD_BASIC in src:
    src = src.replace(OLD_BASIC, NEW_BASIC)
    print('  generateBasicCard: patchet')
    changed = True
elif f'_sx={SRC_X}' in src:
    print('  generateBasicCard: allerede patchet')
else:
    print('  ADVARSEL: generateBasicCard ikke funnet')

if OLD_LOGO in src:
    src = src.replace(OLD_LOGO, NEW_LOGO)
    print('  generateLogoCard: patchet')
    changed = True
elif f'_lsx={SRC_X}' in src:
    print('  generateLogoCard: allerede patchet')
else:
    print('  ADVARSEL: generateLogoCard ikke funnet')

if changed:
    shutil.copy2(TARGET, TARGET + '.nep-bak')
    with open(TARGET, 'w') as f:
        f.write(src)
    print('  Ferdig.')

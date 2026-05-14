#!/usr/bin/env python3
"""Patches surface-entrypoint.mjs with correct NEP logo scaling and info display."""

import sys, shutil

TARGET = '/opt/companion-satellite/satellite/dist/surface-entrypoint.mjs'

try:
    with open(TARGET, 'r') as f:
        src = f.read()
except FileNotFoundError:
    print(f'FEIL: {TARGET} ikke funnet')
    sys.exit(1)

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

NEW_BASIC = '''    const _lh = Math.floor(height * 0.55), _m = 3;
    const _sc = Math.min((width-_m*2)/iconImage.width, (_lh-_m)/iconImage.height);
    const _dw = Math.max(1,Math.floor(iconImage.width*_sc)), _dh = Math.max(1,Math.floor(iconImage.height*_sc));
    context2d.drawImage(iconImage,0,0,iconImage.width,iconImage.height,Math.floor((width-_dw)/2),Math.floor((_lh-_dh)/2),_dw,_dh);
    context2d.textAlign = "left";
    let _y = _lh + 11;
    context2d.font = "bold 10px sans-serif";
    context2d.fillStyle = status === "Connected" ? "#00cc44" : "#ff8800";
    context2d.fillText(status, 5, _y); _y += 11;
    context2d.font = "9px sans-serif";
    context2d.fillStyle = "#aaaaaa";
    context2d.fillText("IP: " + getIPAddress(), 5, _y); _y += 11;
    context2d.fillText(process.env.NEP_ID || "Satellite Pi", 5, _y);'''

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

NEW_LOGO = '''    const _lsc = Math.min((width-4)/iconImage.width,(height-4)/iconImage.height);
    const _ldw = Math.max(1,Math.floor(iconImage.width*_lsc)), _ldh = Math.max(1,Math.floor(iconImage.height*_lsc));
    context2d.drawImage(iconImage,0,0,iconImage.width,iconImage.height,Math.floor((width-_ldw)/2),Math.floor((height-_ldh)/2),_ldw,_ldh);'''

changed = False

if OLD_BASIC in src:
    src = src.replace(OLD_BASIC, NEW_BASIC)
    print('  generateBasicCard: patchet')
    changed = True
elif NEW_BASIC in src:
    print('  generateBasicCard: allerede patchet')
else:
    print('  ADVARSEL: generateBasicCard ikke funnet – hopper over')

if OLD_LOGO in src:
    src = src.replace(OLD_LOGO, NEW_LOGO)
    print('  generateLogoCard: patchet')
    changed = True
elif NEW_LOGO in src:
    print('  generateLogoCard: allerede patchet')
else:
    print('  ADVARSEL: generateLogoCard ikke funnet – hopper over')

if changed:
    shutil.copy2(TARGET, TARGET + '.nep-bak')
    with open(TARGET, 'w') as f:
        f.write(src)
    print('  Ferdig.')

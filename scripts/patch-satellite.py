#!/usr/bin/env python3
"""Patches surface-entrypoint.mjs with correct NEP logo scaling and info display."""

import sys, shutil, re

TARGET = '/opt/companion-satellite/satellite/dist/surface-entrypoint.mjs'

ORIGINAL = TARGET + '.nep-original'

# Crop coordinates: content area of 2000x1126 logo (wheel + 40 mark)
SRC_X, SRC_Y, SRC_W, SRC_H = 60, 80, 1700, 980

try:
    import os
    if not os.path.exists(ORIGINAL):
        with open(TARGET, 'r') as f:
            peek = f.read(16384)
        already_patched = f'_sx={SRC_X}' in peek or '_lmargin=' in peek
        bak = TARGET + '.nep-bak'
        if already_patched and os.path.exists(bak):
            shutil.copy2(bak, ORIGINAL)
            print('  Original hentet fra .nep-bak.')
        elif already_patched:
            print('FEIL: Finner ikke original. Reinstaller companion-satellite og prøv igjen.')
            sys.exit(1)
        else:
            shutil.copy2(TARGET, ORIGINAL)
            print('  Original lagret.')
    # Always patch from original
    shutil.copy2(ORIGINAL, TARGET)
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

NEW_BASIC = f'''    const _sx={SRC_X},_sy={SRC_Y},_sw={SRC_W},_sh={SRC_H},_m=4;
    let _cip='?',_conn='?',_fo='?';
    let _cfg={{logo_pct:34,font_size:9,line_spacing:9,text_x:4,text_y_offset:10,show_companion_ip:true,show_conn_fo:true,show_local_ip:true,show_name:true}};
    try{{const _fsm=process.getBuiltinModule('fs');const _cp=process.getBuiltinModule('child_process');
    try{{_cip=_fsm.readFileSync('/run/nep-ts-failover/companion_ip','utf8').trim()||'?';}}catch{{}}
    try{{_fo=_fsm.existsSync('/home/pi/.nep-ts-failover-disabled')?'AV':'AKT';}}catch{{}}
    try{{const _rt=_cp.execSync('ip route get '+_cip+' 2>/dev/null||echo x',{{encoding:'utf8'}});_conn=_rt.includes('dev eth0')?'LAN':_rt.includes('tailscale')?'TS':'?';}}catch{{}}
    try{{Object.assign(_cfg,JSON.parse(_fsm.readFileSync('/home/pi/health/card-config.json','utf8')));}}catch{{}}
    }}catch{{}}
    const _lh=Math.floor(height*Math.max(15,Math.min(55,_cfg.logo_pct||34))/100);
    const _sc=Math.min((width-_m*2)/_sw,(_lh-4)/_sh);
    const _dw=Math.max(1,Math.floor(_sw*_sc)),_dh=Math.max(1,Math.floor(_sh*_sc));
    context2d.drawImage(iconImage,_sx,_sy,_sw,_sh,Math.floor((width-_dw)/2),Math.floor((_lh-_dh)/2),_dw,_dh);
    const _fz=_cfg.font_size||9;const _ls=_cfg.line_spacing||9;
    const _tx=_cfg.text_x||4;const _ty=_cfg.text_y_offset||10;
    context2d.textAlign="left";
    let _y=_lh+_ty;
    context2d.font="bold "+(_fz+1)+"px sans-serif";
    context2d.fillStyle=status==="Connected"?"#00cc44":"#ff8800";
    context2d.fillText(status,_tx,_y);_y+=(_fz+2);
    context2d.font=_fz+"px sans-serif";
    if(_cfg.show_companion_ip!==false){{context2d.fillStyle="#aaaaaa";context2d.fillText("C:"+_cip,_tx,_y);_y+=_ls;}}
    if(_cfg.show_conn_fo!==false){{context2d.fillStyle=_conn==="LAN"?"#55bbff":_conn==="TS"?"#ffaa00":"#888888";context2d.fillText(_conn+" FO:"+_fo,_tx,_y);_y+=_ls;}}
    if(_cfg.show_local_ip!==false){{context2d.fillStyle="#cccccc";context2d.fillText("IP:"+getIPAddress(),_tx,_y);_y+=_ls;}}
    if(_cfg.show_name!==false){{context2d.fillStyle="#888888";context2d.fillText("{nep_id}",_tx,_y);}}'''

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

LOGO_SHIFT_DOWN = 10  # positive = down from center, negative = up

NEW_LOGO = f'''    const _lmargin=8;
    const _lavailW=Math.max(1,width-_lmargin*2),_lavailH=Math.max(1,height-_lmargin*2);
    const _lsc=Math.min(_lavailW/iconImage.width,_lavailH/iconImage.height);
    const _ldw=Math.max(1,Math.floor(iconImage.width*_lsc)),_ldh=Math.max(1,Math.floor(iconImage.height*_lsc));
    const _ldx=Math.floor((width-_ldw)/2);
    let _ldy=Math.floor((height-_ldh)/2)+{LOGO_SHIFT_DOWN};
    _ldy=Math.max(0,Math.min(_ldy,height-_ldh));
    context2d.drawImage(iconImage,0,0,iconImage.width,iconImage.height,_ldx,_ldy,_ldw,_ldh);'''

changed = False

if OLD_BASIC in src:
    src = src.replace(OLD_BASIC, NEW_BASIC)
    print('  generateBasicCard: patchet')
    changed = True
elif f'_sx={SRC_X}' in src:
    # nep-original inneholder gammel NEP-patch – erstatt med ny versjon
    old_nep = re.search(
        r'    const _sx=' + str(SRC_X) + r',_sy=' + str(SRC_Y) + r',.*?fillText\("[^"]*",4,_y\);',
        src, re.DOTALL
    )
    if old_nep:
        src = src[:old_nep.start()] + NEW_BASIC + src[old_nep.end():]
        print('  generateBasicCard: oppdatert fra gammel NEP-patch')
        changed = True
    else:
        print('  ADVARSEL: generateBasicCard (gammel NEP-patch) ikke funnet')
else:
    print('  ADVARSEL: generateBasicCard ikke funnet')

if OLD_LOGO in src:
    src = src.replace(OLD_LOGO, NEW_LOGO)
    print('  generateLogoCard: patchet')
    changed = True
elif '_lmargin=' in src:
    print('  generateLogoCard: allerede patchet')
else:
    print('  ADVARSEL: generateLogoCard ikke funnet')

if changed:
    shutil.copy2(TARGET, TARGET + '.nep-bak')
    with open(TARGET, 'w') as f:
        f.write(src)
    print('  Ferdig.')

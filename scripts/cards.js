import { readFile } from 'fs/promises';
import { Canvas, loadImage } from '@napi-rs/canvas';
import * as imageRs from '@julusian/image-rs';
import { networkInterfaces } from 'os';
import { execSync } from 'child_process';

export class CardGenerator {
  iconImage;

  async loadIcon() {
    if (!this.iconImage) {
      const rawData = await readFile(new URL('../../assets/icon.png', import.meta.url));
      this.iconImage = await loadImage(rawData);
    }
    return this.iconImage;
  }

  async generateBasicCard(width, height, pixelFormat, remoteIp, status) {
    const iconImage = await this.loadIcon();

    const overSampling = 2;
    const canvasWidth = width * overSampling;
    const canvasHeight = height * overSampling;

    const canvas = new Canvas(canvasWidth, canvasHeight);
    const context2d = canvas.getContext('2d');
    context2d.scale(overSampling, overSampling);

    const conn = getConnType(remoteIp);
    const failCount = getFailCount();
    const localIp = getIPAddress();
    const nepId = process.env.NEP_ID || 'Satellite Pi';

    // Logo fills top 55% of button
    const logoAreaH = Math.floor(height * 0.55);
    const margin = 3;
    const scaleW = (width - margin * 2) / iconImage.width;
    const scaleH = (logoAreaH - margin) / iconImage.height;
    const scale = Math.min(scaleW, scaleH);
    const drawW = Math.max(1, Math.floor(iconImage.width * scale));
    const drawH = Math.max(1, Math.floor(iconImage.height * scale));
    const drawX = Math.floor((width - drawW) / 2);
    const drawY = Math.floor((logoAreaH - drawH) / 2);
    context2d.drawImage(iconImage, 0, 0, iconImage.width, iconImage.height, drawX, drawY, drawW, drawH);

    // Info section below logo
    const isConnected = status === 'Connected';
    const connLabel = conn === 'LAN' ? 'LAN' : conn === 'TS' ? 'Tailscale' : 'Ingen';
    const failLabel = failCount > 0 ? ` (feil: ${failCount})` : '';

    context2d.textAlign = 'left';
    const padX = 5;
    let y = logoAreaH + 11;
    const lineH = 11;

    context2d.font = `bold 10px sans-serif`;
    context2d.fillStyle = isConnected ? '#00cc44' : '#ff8800';
    context2d.fillText(status, padX, y); y += lineH;

    context2d.font = `9px sans-serif`;
    context2d.fillStyle = '#ffffff';
    context2d.fillText(`Nett: ${connLabel}${failLabel}`, padX, y); y += lineH;

    context2d.fillStyle = '#aaaaaa';
    context2d.fillText(`IP: ${localIp}`, padX, y); y += lineH;

    context2d.fillText(nepId, padX, y);

    const rawImage = Buffer.from(context2d.getImageData(0, 0, canvasWidth, canvasHeight).data);
    const computedImage = await imageRs.ImageTransformer.fromBuffer(rawImage, canvasWidth, canvasHeight, 'rgba')
      .scale(width, height, 'Exact')
      .toBuffer(pixelFormat);
    return computedImage.buffer;
  }

  async generateLcdStripCard(width, height, pixelFormat, remoteIp, status) {
    const iconImage = await this.loadIcon();

    const overSampling = 2;
    const canvasWidth = width * overSampling;
    const canvasHeight = height * overSampling;

    const canvas = new Canvas(canvasWidth, canvasHeight);
    const context2d = canvas.getContext('2d');
    context2d.scale(overSampling, overSampling);

    const conn = getConnType(remoteIp);

    const fontSize = 10;
    context2d.font = `normal normal normal ${fontSize}px sans-serif`;
    context2d.textAlign = 'left';
    context2d.fillStyle = '#ffffff';

    const padX = 8;
    const topY = 12;
    const lineGap = 12;

    context2d.fillText(`Status: ${status}`, padX, topY + lineGap * 0);
    context2d.fillText(`Local: ${getIPAddress()}`, padX, topY + lineGap * 1);
    context2d.fillText(`Remote: ${remoteIp}`, padX, topY + lineGap * 2);
    context2d.fillText(`Conn: ${conn}`, padX, topY + lineGap * 3);

    const iconBoundingSize = Math.min(width, height);
    const areaX = width - iconBoundingSize;
    const areaY = 0;
    const areaW = iconBoundingSize;
    const areaH = height;

    const margin = 4;
    const availW = Math.max(1, areaW - margin * 2);
    const availH = Math.max(1, areaH - margin * 2);

    const scale = Math.min(availW / iconImage.width, availH / iconImage.height);
    const drawW = Math.max(1, Math.floor(iconImage.width * scale));
    const drawH = Math.max(1, Math.floor(iconImage.height * scale));
    const drawX = Math.floor(areaX + (areaW - drawW) / 2);
    const drawY = Math.floor(areaY + (areaH - drawH) / 2);

    context2d.drawImage(iconImage, 0, 0, iconImage.width, iconImage.height, drawX, drawY, drawW, drawH);

    const rawImage = Buffer.from(context2d.getImageData(0, 0, canvasWidth, canvasHeight).data);
    const computedImage = await imageRs.ImageTransformer.fromBuffer(rawImage, canvasWidth, canvasHeight, 'rgba')
      .scale(width, height, 'Exact')
      .toBuffer(pixelFormat);
    return computedImage.buffer;
  }

  async generateLogoCard(width, height) {
    const iconImage = await this.loadIcon();

    const canvas = new Canvas(width, height);
    const context2d = canvas.getContext('2d');

    const margin = 8;
    const scale = Math.min((width - margin * 2) / iconImage.width, (height - margin * 2) / iconImage.height);
    const drawW = Math.max(1, Math.floor(iconImage.width * scale));
    const drawH = Math.max(1, Math.floor(iconImage.height * scale));
    const drawX = Math.floor((width - drawW) / 2);
    const shiftDown = 14;
    let drawY = Math.floor((height - drawH) / 2) + shiftDown;
    drawY = Math.max(0, Math.min(drawY, height - drawH));

    context2d.drawImage(iconImage, 0, 0, iconImage.width, iconImage.height, drawX, drawY, drawW, drawH);

    return Buffer.from(context2d.getImageData(0, 0, width, height).data);
  }
}

function getIPAddress() {
  for (const devName in networkInterfaces()) {
    const iface = networkInterfaces()[devName];
    if (iface) {
      for (const alias of iface) {
        if (alias.family === 'IPv4' && alias.address !== '127.0.0.1' && !alias.internal) {
          return alias.address;
        }
      }
    }
  }
  return '0.0.0.0';
}

function getFailCount() {
  try {
    return parseInt(execSync('cat /run/nep-ts-failover/fail.count 2>/dev/null || echo 0',
      { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()) || 0;
  } catch {
    return 0;
  }
}

function getConnType(companionIp) {
  try {
    const out = execSync(`ip route get ${companionIp}`, { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString()
      .trim();
    if (out.includes('dev eth0')) return 'LAN';
    if (out.includes('dev tailscale0')) return 'TS';
    return '?';
  } catch {
    return '?';
  }
}

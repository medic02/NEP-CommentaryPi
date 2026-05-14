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

    const fontSize = 10;
    context2d.font = `normal normal normal ${fontSize}px sans-serif`;
    context2d.textAlign = 'left';
    context2d.fillStyle = '#ffffff';

    const line1 = `Status: ${status}`;
    const line2 = `Local: ${getIPAddress()}`;
    const line3 = `Remote: ${remoteIp}`;
    const line4 = `Conn: ${conn}`;

    const padX = 8;
    const topY = 12;
    const lineGap = 12;

    context2d.fillText(line1, padX, topY + lineGap * 0);
    context2d.fillText(line2, padX, topY + lineGap * 1);
    context2d.fillText(line3, padX, topY + lineGap * 2);
    context2d.fillText(line4, padX, topY + lineGap * 3);

    const textH = topY + lineGap * 4 + 2;

    const areaShiftUp = 30;
    const drawShiftUp = 20;
    const logoPaddingTop = 2;
    const logoPaddingBottom = 4;

    const logoX = 0;
    const logoY = (textH + logoPaddingTop) - areaShiftUp;
    const logoW = width;
    const logoH = height - textH - logoPaddingTop - logoPaddingBottom + areaShiftUp;

    const safeLogoY = Math.max(0, Math.min(logoY, height - 1));
    const safeLogoH = Math.max(1, Math.min(logoH, height - safeLogoY));

    const margin = 4;
    const availW = Math.max(1, logoW - margin * 2);
    const availH = Math.max(1, safeLogoH - margin * 2);

    const scale = Math.min(availW / iconImage.width, availH / iconImage.height);
    const drawW = Math.max(1, Math.floor(iconImage.width * scale));
    const drawH = Math.max(1, Math.floor(iconImage.height * scale));

    const drawX = Math.floor(logoX + (logoW - drawW) / 2);

    let drawY = Math.floor(safeLogoY + (safeLogoH - drawH) / 2) - drawShiftUp;
    const minY = safeLogoY;
    const maxY = safeLogoY + safeLogoH - drawH;
    drawY = Math.max(minY, Math.min(drawY, maxY));

    context2d.drawImage(iconImage, 0, 0, iconImage.width, iconImage.height, drawX, drawY, drawW, drawH);

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

    const drawShiftUp = 8;
    let drawY = Math.floor(areaY + (areaH - drawH) / 2) - drawShiftUp;
    drawY = Math.max(areaY, Math.min(drawY, areaY + areaH - drawH));

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
    const availW = Math.max(1, width - margin * 2);
    const availH = Math.max(1, height - margin * 2);

    const scale = Math.min(availW / iconImage.width, availH / iconImage.height);
    const drawW = Math.max(1, Math.floor(iconImage.width * scale));
    const drawH = Math.max(1, Math.floor(iconImage.height * scale));

    const drawX = Math.floor((width - drawW) / 2);

    const shiftUp = 14;
    let drawY = Math.floor((height - drawH) / 2) - shiftUp;
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

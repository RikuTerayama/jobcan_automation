/**
 * OGP画像生成（Canvas）
 */

class SeoOgpCanvas {
    /**
     * OGP画像のCanvasを作成
     * @param {Object} options - オプション
     * @param {string} options.presetId - プリセットID
     * @param {string} options.title - タイトル
     * @param {string} options.subtitle - サブタイトル
     * @param {string} options.badge - バッジ
     * @param {string} options.author - 作成者
     * @param {string} options.date - 日付
     * @param {string} options.layout - レイアウト（'left' | 'center'）
     * @param {string} options.background - 背景（'light' | 'dark'）
     * @returns {HTMLCanvasElement}
     */
    static createOgpCanvas(options) {
        const preset = SeoOgpPresets.getPresetById(options.presetId);
        if (!preset) {
            throw new Error('無効なプリセットIDです');
        }

        const canvas = document.createElement('canvas');
        canvas.width = preset.width;
        canvas.height = preset.height;

        this.drawOgp(canvas, options);

        return canvas;
    }

    /**
     * OGP画像を描画
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {Object} options - オプション
     */
    static drawOgp(canvas, options) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // 背景色
        const bgColor = options.background === 'dark' 
            ? '#1A1A1A' 
            : '#FFFFFF';
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, width, height);

        // グラデーション装飾（オプション）
        if (options.background === 'dark') {
            const gradient = ctx.createLinearGradient(0, 0, width, height);
            gradient.addColorStop(0, 'rgba(74, 158, 255, 0.1)');
            gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, width, height);
        }

        // テキスト色
        const textColor = options.background === 'dark' ? '#FFFFFF' : '#1A1A1A';
        const subTextColor = options.background === 'dark' 
            ? 'rgba(255, 255, 255, 0.7)' 
            : 'rgba(0, 0, 0, 0.6)';

        // レイアウト設定
        const isLeft = options.layout === 'left';
        const padding = 60;
        const maxWidth = width - (padding * 2);
        let currentY = padding + 40;

        // バッジ（左上）
        if (options.badge) {
            ctx.fillStyle = '#4A9EFF';
            ctx.font = 'bold 24px "Noto Sans JP", sans-serif';
            const badgeMetrics = ctx.measureText(options.badge);
            const badgeWidth = badgeMetrics.width + 20;
            const badgeHeight = 36;
            ctx.fillRect(padding, padding, badgeWidth, badgeHeight);
            ctx.fillStyle = '#FFFFFF';
            ctx.textBaseline = 'middle';
            ctx.fillText(options.badge, padding + 10, padding + badgeHeight / 2);
            currentY += badgeHeight + 20;
        }

        // タイトル
        if (options.title) {
            ctx.fillStyle = textColor;
            ctx.font = 'bold 48px "Noto Sans JP", sans-serif';
            ctx.textBaseline = 'top';
            const titleLines = this.wrapText(ctx, options.title, maxWidth, 48);
            titleLines.forEach((line, index) => {
                const x = isLeft ? padding : (width - ctx.measureText(line).width) / 2;
                ctx.fillText(line, x, currentY);
                currentY += 60;
            });
            currentY += 20;
        }

        // サブタイトル
        if (options.subtitle) {
            ctx.fillStyle = subTextColor;
            ctx.font = '32px "Noto Sans JP", sans-serif';
            ctx.textBaseline = 'top';
            const subtitleLines = this.wrapText(ctx, options.subtitle, maxWidth, 32);
            subtitleLines.forEach((line) => {
                const x = isLeft ? padding : (width - ctx.measureText(line).width) / 2;
                ctx.fillText(line, x, currentY);
                currentY += 45;
            });
            currentY += 30;
        }

        // 作成者と日付（下部）
        const footerY = height - padding - 30;
        if (options.author || options.date) {
            ctx.fillStyle = subTextColor;
            ctx.font = '24px "Noto Sans JP", sans-serif';
            ctx.textBaseline = 'bottom';
            
            let footerText = '';
            if (options.author) {
                footerText += options.author;
            }
            if (options.date) {
                if (footerText) footerText += ' • ';
                footerText += options.date;
            }
            
            if (footerText) {
                const x = isLeft ? padding : (width - ctx.measureText(footerText).width) / 2;
                ctx.fillText(footerText, x, footerY);
            }
        }
    }

    /**
     * テキストを折り返す
     * @param {CanvasRenderingContext2D} ctx - Canvasコンテキスト
     * @param {string} text - テキスト
     * @param {number} maxWidth - 最大幅
     * @param {number} fontSize - フォントサイズ
     * @returns {string[]}
     */
    static wrapText(ctx, text, maxWidth, fontSize) {
        const words = text.split('');
        const lines = [];
        let currentLine = '';

        for (let i = 0; i < words.length; i++) {
            const char = words[i];
            const testLine = currentLine + char;
            const metrics = ctx.measureText(testLine);
            
            if (metrics.width > maxWidth && currentLine.length > 0) {
                lines.push(currentLine);
                currentLine = char;
            } else {
                currentLine = testLine;
            }
        }
        
        if (currentLine.length > 0) {
            lines.push(currentLine);
        }

        return lines.length > 0 ? lines : [text];
    }

    /**
     * CanvasをBlobに変換
     * @param {HTMLCanvasElement} canvas - Canvas要素
     * @param {string} format - 形式（'png' | 'jpeg'）
     * @param {number} quality - 品質（0.1-1.0、JPEGのみ）
     * @returns {Promise<Blob>}
     */
    static async canvasToBlob(canvas, format = 'png', quality = 0.9) {
        return new Promise((resolve, reject) => {
            const mimeType = format === 'jpeg' || format === 'jpg' 
                ? 'image/jpeg' 
                : 'image/png';
            
            const options = {};
            if (mimeType === 'image/jpeg') {
                options.quality = quality;
            }

            canvas.toBlob(
                (blob) => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error('画像変換に失敗しました'));
                    }
                },
                mimeType,
                options.quality
            );
        });
    }
}

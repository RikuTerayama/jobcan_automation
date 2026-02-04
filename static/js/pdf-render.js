/**
 * PDF→画像レンダリングユーティリティ（pdfjs-dist使用）
 */

class PdfRender {
    /**
     * PDFを画像に変換
     * @param {File} file - PDFファイル
     * @param {Object} options - オプション
     * @param {string} options.format - 画像形式 ("png" | "jpeg")
     * @param {number} options.scale - スケール（例: 1.0, 1.5, 2.0）
     * @param {number} options.quality - 品質（JPEGのみ、0.1-1.0）
     * @param {Object} ctx - コンテキスト
     * @returns {Promise<Array<{blob: Blob, filename: string, mime: string}>>}
     */
    static async pdfToImages(file, options = {}, ctx = {}) {
        // pdfjs-distはグローバル変数として読み込まれる想定
        if (typeof pdfjsLib === 'undefined') {
            throw new Error('pdfjs-distライブラリが読み込まれていません');
        }
        
        const pdfjs = pdfjsLib;

        const {
            format = 'png',
            scale = 1.0,
            quality = 0.9
        } = options;

        // Workerの設定
        if (pdfjs.GlobalWorkerOptions) {
            pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }

        if (ctx.signal && ctx.signal.cancelled) {
            throw new Error('キャンセルされました');
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { status: 'running', message: 'PDF読み込み中...' });
        }

        const arrayBuffer = await file.arrayBuffer();
        const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
        const pdf = await loadingTask.promise;
        const numPages = pdf.numPages;

        if (ctx.setProgress) {
            ctx.setProgress(10);
        }

        const outputs = [];

        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
            if (ctx.signal && ctx.signal.cancelled) {
                throw new Error('キャンセルされました');
            }

            if (ctx.setTaskState) {
                ctx.setTaskState(0, { 
                    status: 'running', 
                    message: `ページ ${pageNum}/${numPages} を変換中...` 
                });
            }

            const page = await pdf.getPage(pageNum);
            const viewport = page.getViewport({ scale });

            // Canvasを作成
            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const context = canvas.getContext('2d');

            // ページをレンダリング
            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };

            await page.render(renderContext).promise;

            // Blobに変換
            let blob;
            let mimeType;
            let ext;

            if (format === 'jpeg' || format === 'jpg') {
                mimeType = 'image/jpeg';
                ext = 'jpg';
                blob = await new Promise((resolve, reject) => {
                    canvas.toBlob(
                        (b) => b ? resolve(b) : reject(new Error('画像変換に失敗しました')),
                        mimeType,
                        quality
                    );
                });
            } else {
                mimeType = 'image/png';
                ext = 'png';
                blob = await new Promise((resolve, reject) => {
                    canvas.toBlob(
                        (b) => b ? resolve(b) : reject(new Error('画像変換に失敗しました')),
                        mimeType
                    );
                });
            }

            const baseName = FileUtils.getFilenameWithoutExtension(file.name);
            const filename = FileValidation.sanitizeFilename(`${baseName}_p${pageNum}.${ext}`);

            outputs.push({
                blob,
                filename,
                mime: mimeType
            });

            // 進捗更新
            if (ctx.setProgress) {
                ctx.setProgress(10 + (pageNum / numPages) * 90);
            }

            // メモリ解放
            canvas.width = 0;
            canvas.height = 0;
        }

        if (ctx.setTaskState) {
            ctx.setTaskState(0, { status: 'success', message: '完了' });
        }

        return outputs;
    }
}

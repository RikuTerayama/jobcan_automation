/**
 * 議事録エクスポート機能
 */

class MinutesExport {
    /**
     * Markdownをダウンロード
     * @param {string} text - Markdownテキスト
     * @param {string} filenameBase - ファイル名のベース
     */
    static downloadMarkdown(text, filenameBase = 'minutes') {
        const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
        
        // ファイル名を生成
        const sanitized = FileValidation.sanitizeFilename(filenameBase);
        const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
        const filename = `${sanitized}_${date}.md`;
        
        FileUtils.downloadBlob(blob, filename);
    }

    /**
     * テキストをクリップボードにコピー
     * @param {string} text - コピーするテキスト
     * @returns {Promise<boolean>}
     */
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // フォールバック: 古いブラウザ対応
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                document.body.removeChild(textarea);
                return true;
            } catch (e) {
                document.body.removeChild(textarea);
                return false;
            }
        }
    }

    /**
     * トーストメッセージを表示（簡易版）
     * @param {string} message - メッセージ
     * @param {string} type - タイプ（'success' | 'error'）
     */
    static showToast(message, type = 'success') {
        // 既存のトーストがあれば削除
        const existing = document.getElementById('toast-message');
        if (existing) {
            existing.remove();
        }
        
        const toast = document.createElement('div');
        toast.id = 'toast-message';
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 24px;
            background: ${type === 'success' ? 'rgba(76, 175, 80, 0.9)' : 'rgba(244, 67, 54, 0.9)'};
            color: white;
            border-radius: 8px;
            z-index: 10000;
            font-size: 0.95em;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }
}

/**
 * 議事録エクスポート機能（v2: CSV/JSON対応）
 */

class MinutesExportV2 {
    /**
     * ToDoをCSV形式で生成
     * @param {Array} actions - ToDo配列
     * @returns {string} - CSV文字列
     */
    static buildActionsCsv(actions) {
        const headers = ['タスク', '担当', '期限（原文）', '期限（正規化）', '状態'];
        const rows = [headers.join(',')];
        
        actions.forEach(action => {
            const row = [
                this.escapeCsv(action.title || ''),
                this.escapeCsv(action.owner || ''),
                this.escapeCsv(action.dueRaw || ''),
                this.escapeCsv(action.dueNormalized || ''),
                action.status === 'done' ? '完了' : '未完了'
            ];
            rows.push(row.join(','));
        });
        
        return rows.join('\n');
    }

    /**
     * ToDoをJSON形式で生成
     * @param {Array} actions - ToDo配列
     * @returns {string} - JSON文字列
     */
    static buildActionsJson(actions) {
        const data = actions.map(action => ({
            title: action.title || '',
            owner: action.owner || '',
            dueRaw: action.dueRaw || '',
            dueNormalized: action.dueNormalized || '',
            status: action.status === 'done' ? '完了' : '未完了',
            confidence: action.confidence || 0,
            sources: action.sources || []
        }));
        
        return JSON.stringify(data, null, 2);
    }

    /**
     * CSVをエスケープ
     * @param {string} text - エスケープするテキスト
     * @returns {string}
     */
    static escapeCsv(text) {
        if (text.includes(',') || text.includes('"') || text.includes('\n')) {
            return `"${text.replace(/"/g, '""')}"`;
        }
        return text;
    }

    /**
     * CSVをダウンロード
     * @param {string} text - CSV文字列
     * @param {string} filenameBase - ファイル名のベース
     */
    static downloadCsv(text, filenameBase = 'actions') {
        const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
        const sanitized = FileValidation.sanitizeFilename(filenameBase);
        const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
        const filename = `${sanitized}_${date}.csv`;
        FileUtils.downloadBlob(blob, filename);
    }

    /**
     * JSONをダウンロード
     * @param {string} text - JSON文字列
     * @param {string} filenameBase - ファイル名のベース
     */
    static downloadJson(text, filenameBase = 'actions') {
        const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
        const sanitized = FileValidation.sanitizeFilename(filenameBase);
        const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
        const filename = `${sanitized}_${date}.json`;
        FileUtils.downloadBlob(blob, filename);
    }
}

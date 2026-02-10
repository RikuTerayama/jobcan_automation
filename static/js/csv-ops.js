/**
 * CSV/Excel ユーティリティ - ブラウザ内処理（サーバーへ送信しない）
 * ログにはファイル内容・パスワードを出さず、処理段階・件数のみ記述する。
 */
const CsvOps = {
    MAX_ROWS: 100000,
    PREVIEW_ROWS: 50,

    /**
     * ファイルを UTF-8 テキストとして読み込む
     * @param {File} file
     * @returns {Promise<string>}
     */
    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result || '');
            reader.onerror = () => reject(new Error('ファイルの読み込みに失敗しました'));
            reader.readAsText(file, 'UTF-8');
        });
    },

    /**
     * CSV をパース（PapaParse）。プレビュー用は先頭のみ
     * @param {string} text
     * @param {Object} options - { preview: number }
     * @returns {{ data: string[][], meta: object, previewRows: number }}
     */
    parseCSV(text, options = {}) {
        if (typeof Papa === 'undefined') throw new Error('PapaParse が読み込まれていません');
        if (options.preview != null) {
            const result = Papa.parse(text, { preview: options.preview, skipEmptyLines: true });
            return { data: result.data || [], meta: result.meta || {}, previewRows: (result.data || []).length };
        }
        const full = Papa.parse(text, { skipEmptyLines: true });
        const rows = full.data || [];
        if (rows.length > this.MAX_ROWS) throw new Error(`行数が上限（${this.MAX_ROWS}行）を超えています。`);
        return { data: rows, meta: full.meta || {}, previewRows: rows.length };
    },

    /**
     * 列の抽出・並べ替え（インデックス配列で指定）
     * @param {string[][]} rows
     * @param {number[]} columnIndexes - 0-based
     * @returns {string[][]}
     */
    selectColumns(rows, columnIndexes) {
        if (!rows.length) return [];
        return rows.map(row => columnIndexes.map(i => row[i] != null ? row[i] : ''));
    },

    /**
     * 重複削除（キー列で先頭を残す）
     * @param {string[][]} rows - 1行目がヘッダー
     * @param {number} keyColumnIndex - 0-based
     * @returns {string[][]}
     */
    dedupeByKey(rows, keyColumnIndex) {
        if (!rows.length) return [];
        const header = rows[0];
        const data = rows.slice(1);
        const seen = new Set();
        const out = [header];
        for (const row of data) {
            const key = row[keyColumnIndex] != null ? String(row[keyColumnIndex]) : '';
            if (seen.has(key)) continue;
            seen.add(key);
            out.push(row);
        }
        return out;
    },

    /**
     * N行ごとに分割（1つ目にヘッダーを含む）
     * @param {string[][]} rows - 1行目がヘッダー
     * @param {number} chunkSize
     * @returns {string[][]][]}
     */
    splitByNRows(rows, chunkSize) {
        if (!rows.length || chunkSize < 1) return [];
        const header = rows[0];
        const data = rows.slice(1);
        const chunks = [];
        for (let i = 0; i < data.length; i += chunkSize) {
            chunks.push([header, ...data.slice(i, i + chunkSize)]);
        }
        return chunks;
    },

    /**
     * 二次元配列を CSV 文字列に
     * @param {string[][]} rows
     * @returns {string}
     */
    toCSVString(rows) {
        if (typeof Papa === 'undefined') {
            return rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\r\n');
        }
        return Papa.unparse(rows);
    },

    /**
     * 配列を Blob に
     * @param {string[][]} rows
     * @returns {Blob}
     */
    rowsToBlob(rows) {
        const csv = this.toCSVString(rows);
        return new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    },

    /**
     * ファイル名のベース＋サフィックス＋日付
     * @param {string} base
     * @param {string} suffix
     * @param {string} ext
     * @returns {string}
     */
    outputFilename(base, suffix, ext) {
        const safe = typeof FileValidation !== 'undefined' ? FileValidation.sanitizeFilename(base) : base.replace(/[<>:"/\\|?*]/g, '_');
        const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
        return `${safe}_${suffix}_${date}.${ext}`;
    }
};

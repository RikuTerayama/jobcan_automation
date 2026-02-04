/**
 * 議事録テキストの正規化とノイズ除去
 */

class MinutesNormalize {
    /**
     * ノイズを除去
     * @param {string} line - 行テキスト
     * @returns {string} - ノイズ除去後のテキスト
     */
    static stripNoise(line) {
        if (!line) return '';
        
        let text = line.trim();
        
        // タイムスタンプ除去
        // 例: "00:12:03", "10:31", "[00:12:03]"
        text = text.replace(/\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*/g, '');
        
        // 話者ラベル除去
        // 例: "田中:", "Tanaka:", "10:31 田中:"
        text = text.replace(/^[^\s:：]+[:：]\s*/g, '');
        text = text.replace(/\s+[^\s:：]+[:：]\s*/g, ' ');
        
        // 余計な連続空白を整理
        text = text.replace(/\s+/g, ' ').trim();
        
        return text;
    }

    /**
     * 箇条書きプレフィックスを検出して本文を取り出す
     * @param {string} line - 行テキスト
     * @returns {string} - プレフィックス除去後の本文
     */
    static detectListPrefix(line) {
        if (!line) return '';
        
        let text = line.trim();
        
        // 箇条書き記号や番号を識別
        // 例: "-", "1.", "1)", "・", "•", "*"
        const listPatterns = [
            /^[-•・*]\s+/,           // "- ", "• ", "・ ", "* "
            /^\d+[.)）]\s+/,         // "1. ", "1) ", "1） "
            /^[（(]\d+[）)]\s+/,      // "(1) ", "（1） "
            /^[a-zA-Z][.)）]\s+/,     // "a. ", "A) "
            /^[ivxIVX]+[.)）]\s+/     // "i. ", "IV) "
        ];
        
        for (const pattern of listPatterns) {
            if (pattern.test(text)) {
                text = text.replace(pattern, '').trim();
                break;
            }
        }
        
        return text;
    }

    /**
     * 行を正規化（ノイズ除去 + リストプレフィックス除去）
     * @param {string} line - 行テキスト
     * @returns {string} - 正規化後のテキスト
     */
    static normalizeLine(line) {
        let text = this.stripNoise(line);
        text = this.detectListPrefix(text);
        return text.trim();
    }
}

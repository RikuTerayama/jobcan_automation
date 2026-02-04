/**
 * 日付の正規化
 */

class MinutesDate {
    /**
     * 期限を正規化（YYYY-MM-DD形式に変換）
     * @param {string} dueRaw - 原文の期限
     * @param {string} baseDate - 基準日（YYYY-MM-DD形式、未指定なら今日）
     * @returns {string} - 正規化後の日付（YYYY-MM-DD）、変換できない場合は空文字
     */
    static normalizeDueDate(dueRaw, baseDate = null) {
        if (!dueRaw || dueRaw.trim().length === 0) {
            return '';
        }
        
        const text = dueRaw.trim();
        
        // 基準日を取得
        let base = null;
        if (baseDate) {
            base = this.parseDate(baseDate);
        }
        if (!base) {
            base = new Date();
        }
        
        // 明確な日付表現を優先
        const explicitDate = this.parseExplicitDate(text, base.getFullYear());
        if (explicitDate) {
            return this.formatDate(explicitDate);
        }
        
        // 相対表現を解決
        const relativeDate = this.resolveRelativeDate(text, base);
        if (relativeDate) {
            return this.formatDate(relativeDate);
        }
        
        // 変換できない場合は空文字
        return '';
    }

    /**
     * 明確な日付表現をパース
     * @param {string} text - 日付テキスト
     * @param {number} baseYear - 基準年
     * @returns {Date|null}
     */
    static parseExplicitDate(text, baseYear) {
        // YYYY-MM-DD, YYYY/MM/DD
        const fullDateMatch = text.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
        if (fullDateMatch) {
            const year = parseInt(fullDateMatch[1], 10);
            const month = parseInt(fullDateMatch[2], 10) - 1;
            const day = parseInt(fullDateMatch[3], 10);
            const date = new Date(year, month, day);
            if (this.isValidDate(date)) {
                return date;
            }
        }
        
        // MM/DD, M/D
        const shortDateMatch = text.match(/(\d{1,2})[-/](\d{1,2})/);
        if (shortDateMatch) {
            const month = parseInt(shortDateMatch[1], 10) - 1;
            const day = parseInt(shortDateMatch[2], 10);
            const date = new Date(baseYear, month, day);
            if (this.isValidDate(date)) {
                return date;
            }
        }
        
        // M月D日
        const jpDateMatch = text.match(/(\d{1,2})月(\d{1,2})日/);
        if (jpDateMatch) {
            const month = parseInt(jpDateMatch[1], 10) - 1;
            const day = parseInt(jpDateMatch[2], 10);
            const date = new Date(baseYear, month, day);
            if (this.isValidDate(date)) {
                return date;
            }
        }
        
        return null;
    }

    /**
     * 相対日付表現を解決
     * @param {string} text - 日付テキスト
     * @param {Date} baseDate - 基準日
     * @returns {Date|null}
     */
    static resolveRelativeDate(text, baseDate) {
        const lowerText = text.toLowerCase();
        
        // 本日、今日
        if (lowerText.includes('本日') || lowerText.includes('今日')) {
            return new Date(baseDate);
        }
        
        // 明日
        if (lowerText.includes('明日')) {
            const date = new Date(baseDate);
            date.setDate(date.getDate() + 1);
            return date;
        }
        
        // 明後日
        if (lowerText.includes('明後日')) {
            const date = new Date(baseDate);
            date.setDate(date.getDate() + 2);
            return date;
        }
        
        // 今週
        if (lowerText.includes('今週')) {
            const weekday = this.resolveRelativeWeekday(text, baseDate);
            if (weekday) {
                return weekday;
            }
            // 今週の指定が無い場合は今週の金曜日を想定（簡易）
            const date = new Date(baseDate);
            const dayOfWeek = date.getDay();
            const daysUntilFriday = (5 - dayOfWeek + 7) % 7 || 7;
            date.setDate(date.getDate() + daysUntilFriday);
            return date;
        }
        
        // 来週
        if (lowerText.includes('来週')) {
            const weekday = this.resolveRelativeWeekday(text, baseDate);
            if (weekday) {
                const date = new Date(weekday);
                date.setDate(date.getDate() + 7);
                return date;
            }
            // 来週の指定が無い場合は来週の金曜日を想定（簡易）
            const date = new Date(baseDate);
            const dayOfWeek = date.getDay();
            const daysUntilNextFriday = (5 - dayOfWeek + 7) % 7 + 7;
            date.setDate(date.getDate() + daysUntilNextFriday);
            return date;
        }
        
        // 再来週
        if (lowerText.includes('再来週')) {
            const weekday = this.resolveRelativeWeekday(text, baseDate);
            if (weekday) {
                const date = new Date(weekday);
                date.setDate(date.getDate() + 14);
                return date;
            }
        }
        
        return null;
    }

    /**
     * 相対的な曜日を解決
     * @param {string} text - 日付テキスト
     * @param {Date} baseDate - 基準日
     * @returns {Date|null}
     */
    static resolveRelativeWeekday(text, baseDate) {
        const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
        const weekdayNames = ['日曜', '月曜', '火曜', '水曜', '木曜', '金曜', '土曜'];
        
        for (let i = 0; i < weekdays.length; i++) {
            if (text.includes(weekdayNames[i]) || text.includes(weekdays[i] + '曜')) {
                const date = new Date(baseDate);
                const currentDay = date.getDay();
                const targetDay = i;
                let daysToAdd = (targetDay - currentDay + 7) % 7;
                if (daysToAdd === 0) {
                    daysToAdd = 7; // 同じ曜日の場合は来週
                }
                date.setDate(date.getDate() + daysToAdd);
                return date;
            }
        }
        
        return null;
    }

    /**
     * 日付文字列をパース
     * @param {string} dateStr - 日付文字列（YYYY-MM-DD）
     * @returns {Date|null}
     */
    static parseDate(dateStr) {
        if (!dateStr) return null;
        const date = new Date(dateStr);
        return this.isValidDate(date) ? date : null;
    }

    /**
     * 日付をフォーマット（YYYY-MM-DD）
     * @param {Date} date - 日付オブジェクト
     * @returns {string}
     */
    static formatDate(date) {
        if (!this.isValidDate(date)) return '';
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    /**
     * 有効な日付かチェック
     * @param {Date} date - 日付オブジェクト
     * @returns {boolean}
     */
    static isValidDate(date) {
        return date instanceof Date && !isNaN(date.getTime());
    }
}

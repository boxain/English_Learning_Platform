const MISSING_KEY_NOTICE = '目前沒有這段的中文翻譯。未設定 OPENAI_API_KEY 時，仍可只用英文練習。';
const PENDING_NOTICE = '這段的中文翻譯暫時沒有完成，請稍後重新整理。英文練習不受影響。';

export function chineseLine(segment, translationEnabled) {
  const text = typeof segment?.translation_zh === 'string' ? segment.translation_zh.trim() : '';
  if (text) return { kind: 'translation', text };
  if (translationEnabled) return { kind: 'pending', text: PENDING_NOTICE };
  return { kind: 'disabled', text: MISSING_KEY_NOTICE };
}

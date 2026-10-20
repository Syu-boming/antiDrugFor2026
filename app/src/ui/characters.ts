// 說話者名冊：字幕名牌與小頭像（目前頭像先用色塊，之後換正式頭像圖）。
// 顏色只是輔助辨識，名牌文字才是主要依據（不只靠顏色）。

export interface SpeakerInfo { id: string; name: string; color: string }

export const SPEAKERS: SpeakerInfo[] = [
  { id: 'narrator', name: '旁白', color: '#7d8796' },
  { id: 'zhezhe', name: '折折', color: '#e8a34c' },
  { id: 'xiaoqing', name: '小晴', color: '#4f8bd0' },
  { id: 'xiaoyu', name: '小宇', color: '#5aa36b' },
  { id: 'ale', name: '阿樂叔叔', color: '#b8783f' },
  { id: 'pinan', name: '品安', color: '#9a6cc4' },
  { id: 'nurse', name: '葉護理師', color: '#3e9f99' },
  { id: 'teacher', name: '林老師', color: '#c4708c' },
  { id: 'guard', name: '陳伯伯', color: '#7a8650' },
  { id: 'dispatcher', name: '執勤人員', color: '#5b6f90' },
  { id: 'inviter', name: '邀請者', color: '#8c8c8c' },
];

const byName = new Map(SPEAKERS.map((s) => [s.name, s]));

export function speakerInfo(name: string): SpeakerInfo {
  return byName.get(name) ?? { id: 'unknown', name, color: '#8a8580' };
}

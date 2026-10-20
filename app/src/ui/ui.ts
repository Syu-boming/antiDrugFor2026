// 疊層總管：版面配置與每格更新。
import type { CueTimeline } from '../cues/timeline';
import type { WorldState } from '../engine/world';
import { applyRect, computeLayout, type StageLayout } from './layout';
import { SubtitleView } from './subtitle';
import { QuizCardView } from './quizcard';
import { Badge, LostScreen, ReadyScreen, TitleCardView } from './overlays';

const $ = (id: string): HTMLElement => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`index.html 缺少 #${id}`);
  return el;
};

export class UI {
  readonly viewport = $('viewport');
  readonly stageBox = $('stage-box');
  readonly subBox = $('subtitle-box');
  readonly title = new TitleCardView($('title-card'));
  readonly quiz = new QuizCardView($('quiz-card'));
  readonly subs = new SubtitleView(this.subBox);
  readonly ready = new ReadyScreen($('ready-screen'));
  readonly lost = new LostScreen($('lost-screen'));
  readonly placeholder = new Badge($('badge-placeholder'), '暫代音訊');
  readonly pauseMark = new Badge($('badge-pause'), '暫停中');
  layoutState: StageLayout | null = null;

  /** 依視窗大小重新排版，回傳舞台尺寸 */
  layout(): StageLayout {
    const L = computeLayout(window.innerWidth, window.innerHeight);
    applyRect(this.stageBox, L.stage);
    applyRect(this.subBox, L.subtitle);
    this.subBox.classList.toggle('below', !L.subtitleInside);
    this.viewport.style.setProperty('--H', `${L.H}px`);
    this.layoutState = L;
    return L;
  }

  update(o: { tl: CueTimeline; t: number; world: WorldState; showSubs: boolean; placeholder: boolean; paused: boolean }): void {
    this.title.update(o.world.titleCard);
    this.quiz.update(o.tl.quiz, o.world.quizVisible, o.world.quizReveal, o.world.lamps);
    this.subs.update(o.tl, o.t, !o.showSubs || o.world.quizVisible > 0.01);
    this.placeholder.set(o.placeholder);
    this.pauseMark.set(o.paused);
  }
}

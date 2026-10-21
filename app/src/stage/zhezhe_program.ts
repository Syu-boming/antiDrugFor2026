// 折折接進角色系統：把 zhezhe.ts 的 Zhezhe 包成程式角色（rig:"zhezhe"），每個 cue 重排 zhezhe.* 事件與對嘴，每格依時間重建。
import { Group, type Object3D } from 'three';
import { Zhezhe, type ZhezheEmotion } from './zhezhe';
import { registerProgramRig, type ProgramContext, type ProgramPerformer, type ProgramRigOptions } from './cast';
import type { ActorPlacement } from './perform';
import type { CueTimeline } from '../cues/timeline';
import type { CharacterStart } from '../types/cue';

const EMO: Record<string, ZhezheEmotion> = { smile: 'happy', greet: 'happy', neutral: 'neutral', confused: 'curious', worried: 'worried', surprised: 'curious' };
type V3 = [number, number, number];

class ZhezheProgram implements ProgramPerformer {
  readonly kind = 'program' as const;
  readonly root = new Group();
  private zz: Zhezhe;
  private key = '';
  constructor(readonly place: ActorPlacement, o: ProgramRigOptions) {
    this.zz = new Zhezhe({ position: [place.x, 0, place.z], height: Number(o.config.height ?? 1.0), renderOrder: o.orderBase + 15 });
    this.root.add(this.zz.group);
  }
  get id(): string { return this.place.id; }
  faceState(): { eyes: string; mouth: string } | null {
    if (!this.root.visible) return null;
    const p = this.zz.probe();
    return { eyes: String(p.eyes), mouth: String(p.mouth) };
  }
  addTo(parent: Object3D): void { parent.add(this.root); }
  apply(tl: CueTimeline, t: number, start: CharacterStart | undefined, ctx: ProgramContext): void {
    this.root.visible = !!start && start.visible !== false;
    if (!this.root.visible) return;
    if (ctx.playKey !== this.key) {           // 換 cue、重播、上一步：重排事件（update 是時間的純函式）
      this.key = ctx.playKey;
      this.zz.reset({ pos: [start!.x ?? this.place.x, start!.y ?? 0, start!.z ?? this.place.z], emotion: EMO[start!.emotion ?? 'smile'] ?? 'neutral' });
      for (const a of tl.anims) {
        if (a.target !== this.id) continue;
        const p = a.params as Record<string, unknown>;
        switch (a.name) {
          case 'zhezhe.fold': this.zz.fold(p.form as never, a.duration as never, a.start, { scale: p.scale as number, fumble: p.fumble as never }); break;  // dur 的型別在 zhezhe.ts 是字面值
          case 'zhezhe.emote': this.zz.emote(p.emotion as ZhezheEmotion, a.start); break;
          case 'zhezhe.walkTo': this.zz.walkTo(p.pos as V3, a.duration, a.start); break;
          case 'zhezhe.hopTo': this.zz.hopTo(p.pos as V3, a.duration, p.height as number, a.start); break;
          case 'zhezhe.flyTo': this.zz.flyTo(p.pos as V3, a.duration, p.height as number, a.start); break;
          case 'zhezhe.glideTo': this.zz.glideTo(p.pos as V3, a.duration, a.start); break;
          case 'zhezhe.turn': this.zz.turn(Number(p.yaw ?? 0), a.duration, a.start); break;
          case 'zhezhe.look': this.zz.look(Number(p.yaw ?? 0), a.duration, a.start); break;
          case 'zhezhe.hush': this.zz.hush(a.start); break;
          case 'zhezhe.glow': this.zz.glow(Number(p.to ?? 1), a.duration, a.start); break;
          case 'zhezhe.rise': this.zz.rise(a.duration, a.start); break;
          case 'zhezhe.twitch': this.zz.twitch((p.side as 'l' | 'r' | 'both') ?? 'both', a.start); break;
          case 'zhezhe.blink': this.zz.blink(a.start); break;
          default: break;
        }
      }
      for (const l of tl.lines) if (l.actorId === this.id) { const lip = ctx.lipsync(l.line.lipsyncId ?? l.line.id); if (lip) this.zz.say(lip, l.start); }
    }
    // 題卡模式舞台燈調暗時提高存在感（light 0.55→1 對應 presence 0.2→0.06）
    this.zz.update(t, { presence: 0.06 + 0.14 * Math.min(1, Math.max(0, (1 - ctx.light) / 0.45)) });
  }
}

registerProgramRig('zhezhe', (o) => new ZhezheProgram(o.place, o));

// 舞台特效（全部是緩慢漸變，零閃爍）：
// - FX8 場景降彩：在景片材質的著色器最後（線性色彩空間）以相對亮度為軸降低彩度，亮度不變；
//   角色、操偶線、字幕、題卡都不套用（受影響者的臉、膚色、服裝不能改變——兒童安全界線第 2 條）。
// - FX4 柔和追光：一盞邊緣很軟的聚光燈跟著指定角色（不投影、不掃動、只隨 cue 漸亮漸暗）。
import { Object3D, SpotLight, type Material } from 'three';

export const desatUniform = { value: 0 };

/** 讓材質支援 FX8 降彩（共用同一個 uniform） */
export function enableDesat(mat: Material): void {
  const m = mat as Material & { userData: Record<string, unknown> };
  if (m.userData.desat) return;
  m.userData.desat = true;
  const prev = m.onBeforeCompile;
  m.onBeforeCompile = (shader, renderer) => {
    prev?.call(m, shader, renderer);
    shader.uniforms.uDesat = desatUniform;
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', 'uniform float uDesat;\nvoid main() {')
      .replace('#include <tonemapping_fragment>', `{ float l = dot(gl_FragColor.rgb, vec3(0.2126, 0.7152, 0.0722));
  gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(l), uDesat); }
#include <tonemapping_fragment>`);
  };
  m.customProgramCacheKey = () => 'desat1';
  m.needsUpdate = true;
}

export class FollowSpot {
  readonly light: SpotLight;
  readonly target = new Object3D();
  constructor() {
    this.light = new SpotLight('#fff1dc', 0, 0, 0.2, 0.85, 0);
    this.light.castShadow = false;
    this.light.target = this.target;
    this.light.position.set(0, 14, 16);
  }
  /** @param level 0–1  @param at 追光中心（世界座標） */
  set(level: number, at: [number, number, number] | null, base = 1.6): void {
    this.light.intensity = base * Math.max(0, level);
    if (at) {
      this.target.position.set(at[0], at[1], at[2]);
      this.light.position.set(at[0] + 1.5, at[1] + 11.5, at[2] + 15);
    }
  }
}

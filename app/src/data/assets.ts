// 素材庫：從資料包（data/img_*.js、data/assets_json.js）讀出圖像與素材 JSON，解碼成 HTMLImageElement。
// 圖像 id＝相對 assets/final 的路徑（去掉副檔名與版本號），例如 face/ale/mouth_closed、chr-xiaoqing_master。
import { dataUrlToImage, getPack, loadPackFiles, PackLoadError, type PackManifest } from './packs';

export class AssetStore {
  readonly images = new Map<string, HTMLImageElement>();
  readonly json = new Map<string, unknown>();
  readonly failed: string[] = [];
  manifest: PackManifest | null = null;

  async load(man: PackManifest, onProgress?: (done: number, total: number) => void): Promise<void> {
    this.manifest = man;
    const files = new Set<string>();
    for (const v of Object.values(man.images ?? {})) files.add(v.file);
    for (const v of Object.values(man.json ?? {})) files.add(v.file);
    // 圖像與素材 JSON 都是必要資料包：缺任何一檔就停在準備畫面（等全部載完才丟，訊息不會被進度蓋掉）
    const failed = await loadPackFiles(files, onProgress);
    if (failed.length) throw new PackLoadError(failed, '圖像資料檔');
    for (const id of Object.keys(man.json ?? {})) {
      const d = getPack<unknown>(`json:${id}`);
      if (d !== undefined) this.json.set(id, d);
    }
    await Promise.all(Object.keys(man.images ?? {}).map(async (id) => {
      const url = getPack<string>(`img:${id}`);
      if (!url) { this.failed.push(id); return; }
      try { this.images.set(id, await dataUrlToImage(url)); } catch { this.failed.push(id); }
    }));
  }

  private byBase: Map<string, string> | null = null;

  /** 依 id 取圖；找不到時用檔名（最後一段）找，例如 face.json 的 image_id「chr-ale_mouth_closed」→ face/ale/chr-ale_mouth_closed */
  image(id: string): HTMLImageElement | undefined {
    const hit = this.images.get(id);
    if (hit) return hit;
    if (!this.byBase) {
      this.byBase = new Map();
      const dup = new Set<string>();
      for (const k of this.images.keys()) {
        const b = k.slice(k.lastIndexOf('/') + 1);
        if (this.byBase.has(b)) dup.add(b); else this.byBase.set(b, k);
      }
      dup.forEach((b) => this.byBase!.delete(b));
    }
    const full = this.byBase.get(id.slice(id.lastIndexOf('/') + 1));
    return full ? this.images.get(full) : undefined;
  }
  getJson<T>(id: string): T | undefined { return this.json.get(id) as T | undefined; }
  isFallback(id: string): boolean { return !!this.manifest?.images[id]?.fallback; }
  source(id: string): string { return this.manifest?.images[id]?.source ?? ''; }
}

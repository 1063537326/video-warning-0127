/**
 * 图片 URL 解析工具
 *
 * 统一处理后端返回的图片路径（base64 / URL / 空值），
 * 避免在各组件中重复编写判断逻辑。
 */

/**
 * 解析图片来源，返回可用于 `<img :src>` 的 URL
 *
 * 支持三种输入格式：
 * - `data:image/...` — 已编码的 base64，直接返回
 * - `/static/captures/...` — 后端 URL 路径，直接返回
 * - 其他非空字符串 — 视为裸 base64 数据，添加 `data:image/jpeg;base64,` 前缀
 *
 * @param src - 图片来源字符串（可能为 null / undefined / 空）
 * @returns 可用于 img src 的 URL 字符串，或空字符串
 */
export function resolveImageSrc(src: string | null | undefined): string {
  if (!src) return ''
  if (src.startsWith('data:')) return src
  if (src.startsWith('/')) return src
  return `data:image/jpeg;base64,${src}`
}

/**
 * 从多个候选图片中选取最佳缩略图
 *
 * 优先级：face_image > body_image > full_image
 *
 * @param faceImage - 人脸图片
 * @param bodyImage - 体态截图
 * @param fullImage - 全帧截图
 * @returns 解析后的 img src URL
 */
export function resolveThumbnail(
  faceImage?: string | null,
  bodyImage?: string | null,
  fullImage?: string | null,
): string {
  return resolveImageSrc(faceImage) || resolveImageSrc(bodyImage) || resolveImageSrc(fullImage)
}

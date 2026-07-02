"use client";

import { useState } from "react";

/** Round figure avatar. Filename convention in /public/figures/ is the stable
 *  figure id + ".png" (e.g. "fig-jensen-huang.png"). Falls back to the first
 *  character of the Chinese name if the image is missing or fails to load
 *  (e.g. Morris Chang has no avatar yet). */
export function FigureAvatar({
  figureId,
  nameZh,
  nameEn,
  size = 32,
  className = "",
}: {
  figureId?: string | null;
  nameZh?: string | null;
  nameEn?: string | null;
  size?: number;
  className?: string;
}) {
  const src = figureId ? `/figures/${figureId}.png` : null;
  const [failed, setFailed] = useState(false);

  if (src && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={nameZh || nameEn || ""}
        width={size}
        height={size}
        onError={() => setFailed(true)}
        className={`rounded-full object-cover bg-raised shrink-0 ${className}`}
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <div
      className={`rounded-full bg-raised flex items-center justify-center font-bold text-signal shrink-0 ${className}`}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
    >
      {(nameZh || nameEn || "?").charAt(0)}
    </div>
  );
}

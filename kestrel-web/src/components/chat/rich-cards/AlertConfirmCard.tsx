"use client";

import { useTranslations } from "next-intl";
import { Bell } from "lucide-react";

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    condition: string;
    threshold?: number;
    channels?: string[];
    alert_id?: string;
  };
}

export function AlertConfirmCard({ data }: Props) {
  const t = useTranslations("chat");

  return (
    <div className="my-3 border border-signal/30 rounded-2xl overflow-hidden bg-signal/5 p-4 max-w-sm">
      <div className="flex items-center gap-2 mb-2">
        <Bell className="w-4 h-4 text-signal" />
        <span className="text-sm font-medium">{t("alert_created")}</span>
      </div>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-muted">{t("alert_stock")}</span>
          <span className="font-medium">{data.stock_id}{data.stock_name && ` ${data.stock_name}`}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">{t("alert_condition")}</span>
          <span className="font-mono">{data.condition}{data.threshold != null && ` ${data.threshold}`}</span>
        </div>
        {data.channels && data.channels.length > 0 && (
          <div className="flex justify-between">
            <span className="text-muted">{t("alert_channel")}</span>
            <span>{data.channels.join(" + ")}</span>
          </div>
        )}
      </div>
    </div>
  );
}

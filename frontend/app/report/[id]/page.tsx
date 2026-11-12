import Link from "next/link";
import { ReportLoader } from "@/components/ReportLoader";

export default async function SharedReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="space-y-6">
      <div className="surface flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm text-zinc-400">
        <span>Shared snapshot. It does not update; run a fresh analysis for current data.</span>
        <Link href="/" className="text-radar-300 hover:underline">
          Analyse another repository →
        </Link>
      </div>
      <ReportLoader mode="shared" id={id} />
    </div>
  );
}

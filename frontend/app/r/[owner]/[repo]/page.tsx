import type { Metadata } from "next";
import { ReportLoader } from "@/components/ReportLoader";

type Params = { owner: string; repo: string };

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { owner, repo } = await params;
  return { title: `${owner}/${repo} health report` };
}

export default async function LiveReportPage({ params }: { params: Promise<Params> }) {
  const { owner, repo } = await params;
  return <ReportLoader mode="live" owner={owner} name={repo} />;
}

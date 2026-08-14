import type { Metadata } from "next";
import ResumeEditor from "@/components/ResumeEditor";

export const metadata: Metadata = { title: "Resume | Aus Job Scraper" };

export default function ResumePage() {
  return <ResumeEditor />;
}

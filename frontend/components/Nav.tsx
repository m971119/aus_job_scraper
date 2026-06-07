"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Job Listings" },
  { href: "/applications", label: "Applications" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-4 flex items-center justify-between h-14">
        <span className="text-navy font-bold text-lg">Aus Job Scraper</span>
        <div className="flex gap-1">
          {LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
                pathname === href
                  ? "text-primary bg-primary/10"
                  : "text-muted hover:text-navy"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

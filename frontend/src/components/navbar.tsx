import Link from "next/link";

const navLinks = [
  { href: "/drafts", label: "Drafts", roles: ["creator", "reviewer", "admin"] },
  { href: "/drafts/new", label: "New Draft", roles: ["creator", "admin"] },
  {
    href: "/review-queue",
    label: "Review Queue",
    roles: ["reviewer", "admin"],
  },
  { href: "/sources", label: "Sources", roles: ["admin"] },
  { href: "/insights", label: "Insights", roles: ["admin"] },
];

export default function Navbar() {
  // TODO: Filter links by actual user role once auth is implemented
  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="container mx-auto flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-indigo-600">
          ProofLine
        </Link>
        <div className="flex items-center gap-4">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-gray-600 hover:text-indigo-600 transition-colors"
            >
              {link.label}
            </Link>
          ))}
          <Link
            href="/login"
            className="text-sm bg-indigo-600 text-white px-3 py-1.5 rounded hover:bg-indigo-700 transition-colors"
          >
            Login
          </Link>
        </div>
      </div>
    </nav>
  );
}


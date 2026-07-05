import Link from "next/link";
import { SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
export default function NotFound() { return <div className="mx-auto flex min-h-[70vh] max-w-xl items-center px-4 pt-24"><Card className="w-full"><EmptyState icon={SearchX} title="Nothing here" description="The page may have moved or is no longer available." action={<Link href="/store"><Button>Browse store</Button></Link>} /></Card></div>; }

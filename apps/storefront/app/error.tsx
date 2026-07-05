"use client";
import { WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) { return <div className="mx-auto flex min-h-[70vh] max-w-xl items-center px-4 pt-24"><Card className="w-full"><EmptyState icon={WifiOff} title="RavenStore is temporarily unavailable" description="We could not reach the store right now." action={<Button onClick={reset}>Retry</Button>} /></Card></div>; }

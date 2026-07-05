"use client";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
export default function AdminError({ reset }: { error: Error; reset: () => void }) { return <div className="flex min-h-[60vh] items-center justify-center"><Card className="w-full max-w-md p-6 text-center"><div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg border border-red-400/20 bg-red-400/10 text-red-200"><AlertTriangle className="h-5 w-5" /></div><h1 className="mt-4 text-lg font-semibold">This view could not be loaded</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">Your session is safe. Retry the request or use the command palette to navigate elsewhere.</p><Button className="mt-5" onClick={reset}>Retry view</Button></Card></div>; }

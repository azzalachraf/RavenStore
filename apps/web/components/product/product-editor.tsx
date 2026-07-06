"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { motion } from "framer-motion";
import { ImagePlus, Save, Smartphone, Trash2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ravenApi } from "@/lib/api";
import type { Category, Product } from "@/lib/types";
import { formatCurrency, stableId } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

type DraftProduct = Partial<Product> & {
  title?: string;
  description?: string;
  price?: string;
  duration_days?: string;
  warranty_days?: string;
  stock?: string;
  unlimited_stock?: boolean;
  delivery_type?: string;
  tags?: string;
};

export function ProductEditor({
  open,
  onOpenChange,
  product,
  categories,
  onSaved
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  product?: Product | null;
  categories: Category[];
  onSaved: () => void;
}) {
  const { success, error } = useToast();
  const [draft, setDraft] = React.useState<DraftProduct>({});
  const [accounts, setAccounts] = React.useState<string[]>([""]);
  const [saving, setSaving] = React.useState(false);
  const [pendingImages, setPendingImages] = React.useState<File[]>([]);
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const fileInput = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    const variant = product?.variants?.[0];
    const initialAccounts = product?.product_metadata?.delivery_content_list as string[] | undefined;
    setAccounts(initialAccounts?.length ? initialAccounts : [""]);
    
    setDraft(
      product
        ? {
            ...product,
            title: product.name_key,
            description: product.description_key ?? "",
            price: variant?.price_amount ?? "",
            duration_days: variant?.duration_days ? String(variant.duration_days) : "",
            delivery_type: variant?.delivery_type ?? "account_credentials",
            warranty_days: String(product.product_metadata?.warranty_days ?? ""),
            tags: Array.isArray(product.product_metadata?.tags) ? (product.product_metadata.tags as string[]).join(", ") : ""
          }
        : {
            slug: "",
            title: "",
            description: "",
            status: "active",
            delivery_type: "account_credentials",
            price: "",
            duration_days: "",
            warranty_days: "",
            tags: "",
            images: []
          }
    );
    setPendingImages([]);
  }, [product, open]);

  const save = async () => {
    setSaving(true);
    try {
      const category = draft.category_id ?? categories[0]?.id;
      const activeAccounts = accounts.filter(acc => acc.trim() !== "");
      const payload = {
        expected_updated_at: product?.updated_at,
        category_id: category,
        slug: draft.slug || stableId("product"),
        name_key: draft.title || "products.untitled",
        description_key: draft.description || null,
        status: "active",
        brand: draft.brand ?? null,
        product_metadata: {
          ...(draft.product_metadata ?? {}),
          warranty_days: Number(draft.warranty_days || 0),
          delivery_content_list: activeAccounts,
          tags: draft.tags?.split(",").map((tag) => tag.trim()).filter(Boolean) ?? []
        }
      };
      const saved = product?.id ? await ravenApi.updateProduct(product.id, payload) : await ravenApi.createProduct(payload);
      let variant = product?.variants?.[0];
      const variantPayload = {
          product_id: saved.id,
          sku: `${payload.slug}-default`,
          name_key: `${payload.name_key}.default`,
          duration_days: Number(draft.duration_days || 0) || null,
          region: "global",
          delivery_type: draft.delivery_type || "account_credentials",
          price_amount: Number(draft.price || 0),
          cost_amount: 0,
          currency: "USD",
          is_active: true
      };
      if (variant) {
        variant = await ravenApi.updateVariant(variant.id, {
          name_key: variantPayload.name_key,
          duration_days: variantPayload.duration_days,
          region: variantPayload.region,
          delivery_type: variantPayload.delivery_type,
          price_amount: variantPayload.price_amount,
          cost_amount: variantPayload.cost_amount,
          currency: variantPayload.currency,
          is_active: variantPayload.is_active
        });
      } else if (draft.price) {
        variant = await ravenApi.createVariant(variantPayload);
      }
      if (variant) {
        await ravenApi.updateInventory(variant.id, {
          quantity_available: activeAccounts.length,
          unlimited_stock: activeAccounts.length === 0,
          low_stock_threshold: 5
        });
      }
      for (const image of pendingImages) {
        await ravenApi.uploadProductImage(saved.id, image);
      }
      success("Product synchronized", "Telegram and website clients will read the updated API state.");
      onSaved();
      onOpenChange(false);
    } catch (reason) {
      error("Product could not be saved", reason instanceof Error ? reason.message : "Check the API response and try again.");
    } finally {
      setSaving(false);
    }
  };

  const slugify = (text: string) => text.toLowerCase().trim().replace(/[^\w\s-]/g, "").replace(/[\s_-]+/g, "-").replace(/^-+|-+$/g, "");
  const set = <K extends keyof DraftProduct>(key: K, value: DraftProduct[K]) => {
    setDraft((current) => {
      if (key === "title") {
        return { ...current, title: value, slug: slugify(String(value)) };
      }
      return { ...current, [key]: value };
    });
  };
  const addImages = (files: FileList | File[]) => {
    const images = Array.from(files).filter((file) => ["image/jpeg", "image/png", "image/webp"].includes(file.type));
    setPendingImages((current) => [...current, ...images].slice(0, 12));
  };

  const remove = async () => {
    if (!product?.id) return;
    setSaving(true);
    try {
      await ravenApi.deleteProduct(product.id);
      success("Product hidden", "The archived product is no longer visible to customers.");
      setConfirmDelete(false);
      onSaved();
      onOpenChange(false);
    } catch {
      error("Product could not be hidden");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/55 backdrop-blur-sm" />
        <Dialog.Content asChild>
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            className="fixed bottom-0 right-0 top-0 z-50 w-[1120px] max-w-[100vw] overflow-y-auto border-l border-white/10 bg-[#0a0d14]/95 p-5 shadow-panel backdrop-blur-xl"
          >
            <div className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold">{product ? "Edit product" : "Create product"}</Dialog.Title>
              <div className="flex gap-2">
                {product ? <Button variant="destructive" size="icon" aria-label="Hide product" onClick={() => setConfirmDelete(true)}><Trash2 className="h-4 w-4" /></Button> : null}
                <Button onClick={save} disabled={saving}>
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Sync changes"}
                </Button>
              </div>
            </div>
            <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_360px]">
              <div className="space-y-4">
                <Card className="p-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <Input placeholder="Name" value={draft.title ?? ""} onChange={(e) => set("title", e.target.value)} />
                    <Textarea
                      className="md:col-span-2"
                      placeholder="Description"
                      value={draft.description ?? ""}
                      onChange={(e) => set("description", e.target.value)}
                    />
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="mb-3 text-sm font-medium">Commerce</div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <Input placeholder="Price" value={draft.price ?? ""} onChange={(e) => set("price", e.target.value)} />
                    <Input placeholder="Duration days" value={draft.duration_days ?? ""} onChange={(e) => set("duration_days", e.target.value)} />
                    <Input placeholder="Warranty days" value={draft.warranty_days ?? ""} onChange={(e) => set("warranty_days", e.target.value)} />
                    <Input placeholder="Tags" value={draft.tags ?? ""} onChange={(e) => set("tags", e.target.value)} />
                    <div className="md:col-span-3">
                      <div className="mb-2 text-sm font-medium">Digital Delivery Content</div>
                      {accounts.map((acc, index) => (
                        <div key={index} className="flex gap-2 mb-2 items-center">
                          <Input
                            placeholder={`Account #${index + 1} (e.g. user:pass or link)`}
                            value={acc}
                            onChange={(e) => {
                              const newAccs = [...accounts];
                              newAccs[index] = e.target.value;
                              setAccounts(newAccs);
                            }}
                            className="flex-1"
                          />
                          {accounts.length > 1 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              onClick={() => {
                                setAccounts(accounts.filter((_, i) => i !== index));
                              }}
                            >
                              Remove
                            </Button>
                          )}
                        </div>
                      ))}
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        className="mt-2 text-xs"
                        onClick={() => setAccounts([...accounts, ""])}
                      >
                        + Add a new line
                      </Button>
                    </div>
                  </div>
                </Card>
                <Card
                  className="flex min-h-36 items-center justify-center border-dashed p-4 text-center text-sm text-muted-foreground"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); addImages(e.dataTransfer.files); }}
                  onClick={() => fileInput.current?.click()}
                >
                  <div>
                    <input ref={fileInput} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => e.target.files && addImages(e.target.files)} />
                    <UploadCloud className="mx-auto mb-2 h-8 w-8 text-violet-200" />
                    Drag product images here or click to browse
                    {pendingImages.length ? <div className="mt-2 text-violet-200">{pendingImages.length} image{pendingImages.length === 1 ? "" : "s"} ready</div> : null}
                  </div>
                </Card>
              </div>
              <div className="space-y-4">
                <Preview title="Telegram preview" icon={<Smartphone className="h-4 w-4" />} draft={draft} />
                <Preview title="Website preview" icon={<ImagePlus className="h-4 w-4" />} draft={draft} wide />
                <Preview title="Mobile checkout" icon={<Smartphone className="h-4 w-4" />} draft={draft} />
              </div>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
      <ConfirmDialog open={confirmDelete} onOpenChange={setConfirmDelete} title="Hide this product?" description="Customers will stop seeing it immediately. Existing orders remain unchanged." onConfirm={() => void remove()} />
    </Dialog.Root>
  );
}

function Preview({ title, icon, draft, wide }: { title: string; icon: React.ReactNode; draft: DraftProduct; wide?: boolean }) {
  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <div className={wide ? "rounded-lg border border-border p-4" : "mx-auto max-w-[260px] rounded-[28px] border border-border p-3"}>
        <div className="rounded-lg bg-white/[0.05] p-3">
          <div className="text-sm font-semibold">{draft.title || "products.untitled"}</div>
          <div className="mt-2 text-xs text-muted-foreground">{draft.description || "products.description"}</div>
          <div className="mt-3 text-lg font-semibold">{formatCurrency(Number(draft.price || 0))}</div>
          <div className="mt-3 rounded-md bg-primary px-3 py-2 text-center text-xs font-medium text-primary-foreground">Buy</div>
        </div>
      </div>
    </Card>
  );
}

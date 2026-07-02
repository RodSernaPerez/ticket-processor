create table if not exists public.tickets_gastos (
    id text primary key,
    merchant text not null,
    purchased_at timestamptz not null,
    source_message_id text not null,
    source_attachment_id text not null,
    source_attachment_name text not null,
    products jsonb not null,
    total_amount numeric(12, 2) not null,
    raw_text text not null,
    created_at timestamptz not null default now()
);

create index if not exists tickets_gastos_purchased_at_idx
    on public.tickets_gastos (purchased_at desc);

create index if not exists tickets_gastos_source_message_id_idx
    on public.tickets_gastos (source_message_id);

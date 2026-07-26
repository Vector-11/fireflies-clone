import { cn } from "@/lib/utils";
import { initials, speakerColor } from "@/lib/format";

const SIZES = {
  xs: "h-5 w-5 text-[9px]",
  sm: "h-6 w-6 text-[10px]",
  md: "h-8 w-8 text-[11px]",
  lg: "h-10 w-10 text-sm",
} as const;

/**
 * Initials avatar. There are no real profile photos in this dataset, so the
 * colour carries the identity — and it is derived from the speaker's stored
 * `color_key` rather than hashed at render time, so the same person is the same
 * colour in the transcript, the participant list and the action items.
 */
export function Avatar({
  name,
  colorKey = 0,
  size = "md",
  className,
  title,
}: {
  name: string | null | undefined;
  colorKey?: number;
  size?: keyof typeof SIZES;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title ?? name ?? undefined}
      style={{ backgroundColor: speakerColor(colorKey) }}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white ring-2 ring-white",
        SIZES[size],
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}

/** Overlapping row of avatars, with a "+N" chip once the list runs long. */
export function AvatarStack({
  people,
  max = 4,
  size = "sm",
}: {
  people: { name: string | null; email: string }[];
  max?: number;
  size?: keyof typeof SIZES;
}) {
  const shown = people.slice(0, max);
  const overflow = people.length - shown.length;

  return (
    <div className="flex items-center -space-x-1.5">
      {shown.map((person, index) => (
        <Avatar
          key={person.email}
          name={person.name ?? person.email}
          colorKey={index}
          size={size}
          title={person.name ? `${person.name} · ${person.email}` : person.email}
        />
      ))}
      {overflow > 0 ? (
        <span
          className={cn(
            "inline-flex shrink-0 items-center justify-center rounded-full bg-grey-100 font-semibold text-grey-600 ring-2 ring-white",
            SIZES[size],
          )}
          title={people
            .slice(max)
            .map((person) => person.name ?? person.email)
            .join(", ")}
        >
          +{overflow}
        </span>
      ) : null}
    </div>
  );
}

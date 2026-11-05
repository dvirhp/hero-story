/** Decorative vector artwork; no generated imagery, external assets or story illustrations. */
export function GardenArt({ compact = false }: { compact?: boolean }) {
  return (
    <svg
      className={`garden-art ${compact ? "compact" : ""}`}
      viewBox="0 0 500 540"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id="sky"
          x1="100"
          y1="40"
          x2="400"
          y2="500"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#d4e1d6" />
          <stop offset="1" stopColor="#f0e4c9" />
        </linearGradient>
      </defs>
      <path
        d="M50 482V238C50 117 139 34 250 34s200 83 200 204v244H50Z"
        fill="url(#sky)"
      />
      <circle cx="330" cy="151" r="48" fill="#fff9dc" />
      <circle cx="347" cy="136" r="44" fill="#d9e4d6" />
      <path
        d="m139 119 3 10 10 3-10 3-3 10-3-10-10-3 10-3 3-10ZM374 252l3 8 8 3-8 3-3 8-3-8-8-3 8-3 3-8Z"
        fill="#b78442"
      />
      <g fill="#fff8e2">
        <circle cx="210" cy="99" r="3" />
        <circle cx="386" cy="202" r="3" />
        <circle cx="99" cy="225" r="3" />
        <circle cx="271" cy="186" r="3" />
      </g>
      <path
        d="M50 410c87-80 190-47 249 7 51-62 105-53 151-30v95H50v-72Z"
        fill="#87a998"
      />
      <path
        d="M50 461c74-53 140-33 210-10 65 21 115-51 190-15v46H50v-21Z"
        fill="#527e6b"
      />
      <path
        d="M256 420c-4-71-13-130 12-190"
        stroke="#305f50"
        strokeWidth="5"
        strokeLinecap="round"
      />
      <path d="M253 341c-56 1-87-27-87-69 47-1 85 27 87 69Z" fill="#305f50" />
      <path d="M255 305c53-3 77-30 75-65-45 3-73 23-75 65Z" fill="#6a9277" />
      <path d="M266 254c-20-25-19-50 4-69 21 26 21 48-4 69Z" fill="#b79659" />
      <path
        d="M152 398c32-9 65 2 98 26 33-24 66-35 98-26v76c-34-9-67 2-98 23-32-21-64-32-98-23v-76Z"
        fill="#fff9e9"
        stroke="#d6c6a1"
        strokeWidth="2"
      />
      <path d="M250 424v73" stroke="#c9b58b" strokeWidth="2" />
      <path
        d="m172 422 55 16m-55 0 55 16m101-32-55 16m55 0-55 16"
        stroke="#d7caae"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M111 465c-9-43-33-61-46-65 0 37 16 59 46 65ZM392 477c5-43 22-66 44-73-1 36-16 64-44 73Z"
        fill="#214f49"
      />
      <ellipse cx="250" cy="518" rx="106" ry="5" fill="#214f49" opacity=".08" />
    </svg>
  );
}

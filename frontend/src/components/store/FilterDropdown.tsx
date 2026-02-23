import { useState, useRef, useEffect } from "react";
import { ChevronDown, X, Check } from "lucide-react";

interface FilterDropdownProps {
    label: string;
    options: string[] | { id: number; label: string; value: string }[];
    selected: string[];
    onToggle: (value: string) => void;
    onClear?: () => void;
    color?: "violet" | "emerald" | "blue";
    align?: "left" | "right";
}

export function FilterDropdown({
    label,
    options,
    selected,
    onToggle,
    onClear,
    color = "violet",
    align = "left"
}: FilterDropdownProps) {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Close when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Helpers
    const getLabel = (opt: string | { label: string }) => typeof opt === 'string' ? opt : opt.label;
    const getValue = (opt: string | { value: string }) => typeof opt === 'string' ? opt : opt.value;

    const activeColorClass = {
        violet: "bg-violet-600 text-white border-violet-500",
        emerald: "bg-emerald-600 text-white border-emerald-500",
        blue: "bg-blue-600 text-white border-blue-500"
    }[color];

    return (
        <div className="relative z-50" ref={containerRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`
          flex items-center gap-2 px-4 py-3 rounded-xl border transition-all duration-200
          ${selected.length > 0
                        ? `${activeColorClass} shadow-lg shadow-${color}-900/20`
                        : "bg-zinc-900/50 border-white/10 text-zinc-400 hover:border-white/20 hover:text-white"
                    }
        `}
            >
                <span className="font-medium">{label}</span>
                {selected.length > 0 && (
                    <span className="flex items-center justify-center bg-black/20 rounded-full w-5 h-5 text-xs font-bold">
                        {selected.length}
                    </span>
                )}
                <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>

            {isOpen && (
                <div className={`absolute top-full mt-2 w-[320px] md:w-[600px] z-50 p-4 bg-[#18181b] border border-white/10 rounded-xl shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100 ${align === "right" ? "right-0" : "left-0"}`}>
                    <div className="flex items-center justify-between mb-3 pb-3 border-b border-white/5">
                        <span className="text-sm font-medium text-white">Select {label}</span>
                        {selected.length > 0 && onClear && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onClear(); setIsOpen(false); }}
                                className="text-xs text-zinc-500 hover:text-white transition-colors flex items-center gap-1"
                            >
                                <X className="w-3 h-3" /> Clear all
                            </button>
                        )}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                        {options.map((option) => {
                            const val = getValue(option);
                            const lbl = getLabel(option);
                            const isSelected = selected.includes(val);

                            return (
                                <button
                                    key={val}
                                    onClick={() => onToggle(val)}
                                    className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-all
                    ${isSelected
                                            ? "bg-white/10 text-white font-medium"
                                            : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
                                        }
                  `}
                                >
                                    <div className={`
                    w-4 h-4 rounded border flex items-center justify-center transition-colors
                    ${isSelected
                                            ? `bg-${color}-500 border-${color}-500`
                                            : "border-zinc-700 bg-zinc-900 group-hover:border-zinc-600"
                                        }
                  `}>
                                        {isSelected && <Check className="w-3 h-3 text-white" />}
                                    </div>
                                    <span className="truncate">{lbl}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}

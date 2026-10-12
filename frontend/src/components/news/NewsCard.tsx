import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calendar, User, ArrowRight, Clock, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { getImageUrl } from "@/lib/api";

export interface NewsPost {
    id: number;
    title: string;
    excerpt?: string;
    cover_image_url?: string;
    is_pinned: boolean;
    tags?: string[];
    published_at: string;
    author_display_name?: string;
    content?: string;
}

interface NewsCardProps {
    post: NewsPost;
    featured?: boolean;
}

export function NewsCard({ post, featured = false }: NewsCardProps) {
    const date = new Date(post.published_at).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });

    const readTime = Math.max(1, Math.ceil((post.content?.split(/\s+/).length || 100) / 200));

    if (featured) {
        return (
            <Link to={`/news/${post.id}`} className="block group">
                <div className="relative w-full min-h-[380px] md:min-h-[420px] rounded-2xl overflow-hidden border border-white/10 bg-zinc-950 hover:border-violet-500/50 transition-all duration-300 shadow-2xl hover:shadow-violet-600/10">
                    {/* Background Cover Art */}
                    <div className="absolute inset-0">
                        {post.cover_image_url ? (
                            <img
                                src={getImageUrl(post.cover_image_url)}
                                alt={post.title}
                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                            />
                        ) : (
                            <div className="w-full h-full bg-gradient-to-br from-violet-950 via-zinc-900 to-indigo-950" />
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/70 to-transparent" />
                    </div>

                    {/* Content Overlay */}
                    <div className="absolute bottom-0 inset-x-0 p-6 sm:p-8 flex flex-col gap-3.5 z-10">
                        <div className="flex items-center gap-2 flex-wrap">
                            <Badge className="bg-violet-600 hover:bg-violet-500 text-white font-bold tracking-wide uppercase text-[11px] px-2.5 py-0.5 shadow-md flex items-center gap-1">
                                <Sparkles className="w-3 h-3 fill-current" />
                                Featured Update
                            </Badge>
                            {post.tags?.slice(0, 3).map(tag => (
                                <Badge key={tag} variant="outline" className="bg-zinc-900/60 backdrop-blur-md border-white/10 text-zinc-300 text-xs capitalize">
                                    {tag}
                                </Badge>
                            ))}
                        </div>

                        <h2 className="text-2xl sm:text-4xl font-extrabold text-white leading-tight group-hover:text-violet-300 transition-colors drop-shadow-md">
                            {post.title}
                        </h2>

                        {post.excerpt && (
                            <p className="text-sm sm:text-base text-zinc-300 max-w-3xl line-clamp-2 leading-relaxed drop-shadow">
                                {post.excerpt}
                            </p>
                        )}

                        <div className="flex items-center gap-5 text-xs text-zinc-400 pt-2 border-t border-white/10">
                            <div className="flex items-center gap-1.5">
                                <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                                <span>{date}</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <Clock className="w-3.5 h-3.5 text-zinc-500" />
                                <span>{readTime} min read</span>
                            </div>
                            {post.author_display_name && (
                                <div className="flex items-center gap-1.5">
                                    <User className="w-3.5 h-3.5 text-zinc-500" />
                                    <span>{post.author_display_name}</span>
                                </div>
                            )}
                            <div className="flex items-center gap-1 text-violet-400 group-hover:translate-x-1 transition-transform ml-auto font-semibold">
                                Read Article <ArrowRight className="w-3.5 h-3.5" />
                            </div>
                        </div>
                    </div>
                </div>
            </Link>
        );
    }

    return (
        <Link to={`/news/${post.id}`} className="block h-full group">
            <Card className="h-full overflow-hidden border-white/10 hover:border-violet-500/50 bg-zinc-900/60 hover:bg-zinc-900/90 transition-all duration-300 flex flex-col rounded-2xl hover:shadow-xl hover:shadow-violet-600/10 hover:-translate-y-1">
                {/* Thumbnail */}
                <div className="relative aspect-video overflow-hidden bg-zinc-950">
                    {post.cover_image_url ? (
                        <img
                            src={getImageUrl(post.cover_image_url)}
                            alt={post.title}
                            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                            loading="lazy"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-violet-950/30 to-zinc-900">
                            <span className="text-zinc-700 text-3xl font-extrabold tracking-wider">NEWS</span>
                        </div>
                    )}
                    <div className="absolute top-3 left-3 flex gap-1.5 flex-wrap">
                        {post.tags?.slice(0, 2).map(tag => (
                            <Badge key={tag} variant="secondary" className="backdrop-blur-md bg-zinc-950/70 border border-white/10 text-zinc-300 text-[10px] capitalize">
                                {tag}
                            </Badge>
                        ))}
                    </div>
                </div>

                <CardContent className="flex flex-col flex-grow p-5 gap-3">
                    <div className="flex items-center justify-between text-xs text-zinc-400">
                        <div className="flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                            <span>{date}</span>
                        </div>
                        <span className="text-zinc-500 text-[11px]">{readTime} min</span>
                    </div>

                    <h3 className="text-base sm:text-lg font-bold text-white leading-snug group-hover:text-violet-300 transition-colors line-clamp-2">
                        {post.title}
                    </h3>

                    {post.excerpt && (
                        <p className="text-xs sm:text-sm text-zinc-400 line-clamp-2 leading-relaxed">
                            {post.excerpt}
                        </p>
                    )}

                    <div className="mt-auto pt-3 flex items-center justify-between border-t border-white/5">
                        <span className="text-xs text-zinc-500 truncate">
                            By {post.author_display_name || 'Admin'}
                        </span>
                        <div className="flex items-center gap-1 text-xs font-semibold text-violet-400 group-hover:translate-x-1 transition-transform">
                            Read <ArrowRight className="w-3.5 h-3.5" />
                        </div>
                    </div>
                </CardContent>
            </Card>
        </Link>
    );
}

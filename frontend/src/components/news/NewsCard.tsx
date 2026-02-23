
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calendar, User, ArrowRight } from "lucide-react";
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
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    });

    if (featured) {
        return (
            <Link to={`/news/${post.id}`}>
                <div className="group relative w-full h-[400px] rounded-xl overflow-hidden cursor-pointer border border-border/50 bg-card hover:border-primary/50 transition-all duration-300">
                    <div className="absolute inset-0">
                        {post.cover_image_url ? (
                            <img
                                src={getImageUrl(post.cover_image_url)}
                                alt={post.title}
                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                            />
                        ) : (
                            <div className="w-full h-full bg-gradient-to-br from-primary/20 via-background to-background" />
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />
                    </div>

                    <div className="absolute bottom-0 left-0 right-0 p-8 flex flex-col gap-4">
                        <div className="flex items-center gap-2">
                            <Badge variant="default" className="bg-primary text-primary-foreground">Featured Update</Badge>
                            {post.tags?.map(tag => (
                                <Badge key={tag} variant="outline" className="bg-background/50 backdrop-blur-sm border-white/20 text-white">
                                    {tag}
                                </Badge>
                            ))}
                        </div>

                        <h1 className="text-3xl md:text-4xl font-bold text-white leading-tight group-hover:text-primary transition-colors">
                            {post.title}
                        </h1>

                        {post.excerpt && (
                            <p className="text-lg text-white/80 max-w-2xl line-clamp-2">
                                {post.excerpt}
                            </p>
                        )}

                        <div className="flex items-center gap-6 text-sm text-white/60 mt-2">
                            <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                <span>{date}</span>
                            </div>
                            {post.author_display_name && (
                                <div className="flex items-center gap-2">
                                    <User className="w-4 h-4" />
                                    <span>{post.author_display_name}</span>
                                </div>
                            )}
                            <div className="flex items-center gap-1 text-primary group-hover:translate-x-1 transition-transform ml-auto">
                                Read Article <ArrowRight className="w-4 h-4" />
                            </div>
                        </div>
                    </div>
                </div>
            </Link>
        );
    }

    return (
        <Link to={`/news/${post.id}`}>
            <Card className="group h-full overflow-hidden hover:border-primary/50 transition-all duration-300 cursor-pointer flex flex-col bg-card/50 backdrop-blur-sm">
                <div className="relative h-48 overflow-hidden bg-muted">
                    {post.cover_image_url ? (
                        <img
                            src={getImageUrl(post.cover_image_url)}
                            alt={post.title}
                            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center bg-secondary/20">
                            <span className="text-muted-foreground text-4xl font-bold opacity-20">NEWS</span>
                        </div>
                    )}
                    <div className="absolute top-3 left-3 flex gap-2">
                        {post.tags?.slice(0, 2).map(tag => (
                            <Badge key={tag} variant="secondary" className="backdrop-blur-md bg-background/80 shadow-sm">
                                {tag}
                            </Badge>
                        ))}
                    </div>
                </div>

                <CardContent className="flex flex-col flex-grow p-5 gap-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                        <Calendar className="w-3 h-3" />
                        <span>{date}</span>
                    </div>

                    <h3 className="text-xl font-bold leading-tight group-hover:text-primary transition-colors line-clamp-2">
                        {post.title}
                    </h3>

                    {post.excerpt && (
                        <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                            {post.excerpt}
                        </p>
                    )}

                    <div className="mt-auto pt-4 flex items-center justify-between border-t border-border/50">
                        <span className="text-xs text-muted-foreground">
                            By {post.author_display_name || 'Admin'}
                        </span>
                        <ArrowRight className="w-4 h-4 text-primary opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                    </div>
                </CardContent>
            </Card>
        </Link>
    );
}

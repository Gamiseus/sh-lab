import { useState, useEffect } from "react";
import { X, Loader2, Lock, Users, Globe, Upload, Image as ImageIcon, Trash2, Check } from "lucide-react";
import { profilesAPI, PublicProfile, ProfileUpdate, getImageUrl, ImageInfo } from "@/lib/api";

interface ImageSelectionModalProps {
    type: 'avatar' | 'background';
    onSelect: (url: string) => void;
    onClose: () => void;
}

function ImageSelectionModal({ type, onSelect, onClose }: ImageSelectionModalProps) {
    const [tab, setTab] = useState<'upload' | 'library' | 'presets'>('library');
    const [userImages, setUserImages] = useState<ImageInfo[]>([]);
    const [presetImages, setPresetImages] = useState<ImageInfo[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);

    useEffect(() => {
        loadImages();
    }, [tab, type]);

    const loadImages = async () => {
        setIsLoading(true);
        try {
            if (tab === 'library') {
                const imgs = await profilesAPI.listImages(type);
                setUserImages(imgs);
            } else if (tab === 'presets') {
                const imgs = await profilesAPI.listServerImages(type);
                setPresetImages(imgs);
            }
        } catch (e) {
            console.error("Failed to load images", e);
        } finally {
            setIsLoading(false);
        }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setUploadError(null);
        try {
            const formData = new FormData();
            formData.append("file", file);
            const result = await profilesAPI.uploadImage(type, formData);
            onSelect(result.url); // Select immediately
        } catch (err) {
            setUploadError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async (filename: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("Delete this image?")) return;
        try {
            await profilesAPI.deleteImage(filename, type);
            loadImages(); // Refresh
        } catch (e) {
            alert("Failed to delete image");
        }
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
            <div className="relative bg-zinc-900 border border-white/10 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-white/10">
                    <h3 className="text-lg font-semibold text-white capitalize">Select {type}</h3>
                    <button onClick={onClose} className="p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-white/5">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex gap-1 p-2 bg-zinc-950/50 border-b border-white/5">
                    {(['library', 'presets', 'upload'] as const).map((t) => (
                        <button
                            key={t}
                            onClick={() => setTab(t)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t ? "bg-zinc-800 text-white" : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                                }`}
                        >
                            {t === 'library' ? 'My Library' : t === 'presets' ? 'Presets' : 'Upload New'}
                        </button>
                    ))}
                </div>

                <div className="flex-1 overflow-y-auto p-4 min-h-[300px]">
                    {tab === 'upload' && (
                        <div className="flex flex-col items-center justify-center h-full border-2 border-dashed border-zinc-700 rounded-xl bg-zinc-900/50 hover:bg-zinc-900 transition-colors p-8">
                            <input
                                type="file"
                                accept="image/*"
                                onChange={handleUpload}
                                className="hidden"
                                id="file-upload"
                                disabled={isUploading}
                            />
                            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-4 text-center">
                                <div className="w-16 h-16 rounded-full bg-zinc-800 flex items-center justify-center">
                                    {isUploading ? <Loader2 className="w-8 h-8 animate-spin text-violet-500" /> : <Upload className="w-8 h-8 text-zinc-400" />}
                                </div>
                                <div>
                                    <h4 className="text-lg font-medium text-white">Click to upload image</h4>
                                    <p className="text-sm text-zinc-500 mt-1">JPG, PNG, GIF up to 5MB</p>
                                </div>
                            </label>
                            {uploadError && <p className="mt-4 text-sm text-red-400">{uploadError}</p>}
                        </div>
                    )}

                    {(tab === 'library' || tab === 'presets') && (
                        isLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
                            </div>
                        ) : (
                            <div className="grid grid-cols-3 sm:grid-cols-4 gap-4">
                                {tab === 'library' && userImages.length === 0 && (
                                    <div className="col-span-full text-center py-12 text-zinc-500">
                                        No images uploaded yet.
                                    </div>
                                )}

                                {(tab === 'library' ? userImages : presetImages).map((item) => {
                                    const url = typeof item === 'string' ? item : item.url;
                                    const fullUrl = getImageUrl(url) || "";

                                    return (
                                        <div
                                            key={url}
                                            onClick={() => onSelect(url)}
                                            className="group relative aspect-square rounded-lg overflow-hidden border border-white/10 bg-zinc-800 cursor-pointer hover:border-violet-500 transition-all"
                                        >
                                            <img src={fullUrl} alt="" className="w-full h-full object-cover" />
                                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                                <Check className="w-6 h-6 text-white" />
                                            </div>

                                            {tab === 'library' && typeof item !== 'string' && (
                                                <button
                                                    onClick={(e) => handleDelete(item.filename || "", e)}
                                                    className="absolute top-1 right-1 p-1.5 bg-black/50 hover:bg-red-500/80 rounded-md text-white opacity-0 group-hover:opacity-100 transition-all"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )
                    )}
                </div>
            </div>
        </div>
    );
}

interface ProfileEditModalProps {
    profile: PublicProfile;
    onClose: () => void;
    onSaved: () => void;
}

export function ProfileEditModal({ profile, onClose, onSaved }: ProfileEditModalProps) {
    const [displayName, setDisplayName] = useState(profile.display_name || "");
    const [bio, setBio] = useState(profile.bio || "");
    const [avatarUrl, setAvatarUrl] = useState(profile.avatar_url || "");
    const [backgroundUrl, setBackgroundUrl] = useState(profile.background_url || "");
    const [privacyLevel, setPrivacyLevel] = useState(profile.privacy_level);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeSelector, setActiveSelector] = useState<'avatar' | 'background' | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsSaving(true);

        try {
            const update: ProfileUpdate = {
                display_name: displayName || undefined,
                bio: bio || undefined,
                avatar_url: avatarUrl || undefined,
                background_url: backgroundUrl || undefined,
                privacy_level: privacyLevel,
            };

            await profilesAPI.updateProfile(update);
            onSaved();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to save profile");
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-white/10">
                    <h2 className="text-xl font-semibold text-white">Edit Profile</h2>
                    <button
                        onClick={onClose}
                        className="p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Display Name */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">
                            Display Name
                        </label>
                        <input
                            type="text"
                            value={displayName}
                            onChange={(e) => setDisplayName(e.target.value)}
                            placeholder="Your display name"
                            className="w-full px-4 py-3 bg-zinc-800/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
                        />
                    </div>

                    {/* Bio */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">Bio</label>
                        <textarea
                            value={bio}
                            onChange={(e) => setBio(e.target.value)}
                            placeholder="Tell us about yourself..."
                            rows={3}
                            className="w-full px-4 py-3 bg-zinc-800/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
                        />
                    </div>

                    {/* Avatar URL */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">
                            Avatar
                        </label>
                        <div className="flex items-start gap-4 p-3 bg-zinc-800/30 rounded-lg border border-white/5">
                            <div className="w-16 h-16 rounded-full overflow-hidden bg-zinc-800 border-2 border-zinc-700 flex-shrink-0">
                                {avatarUrl ? (
                                    <img src={getImageUrl(avatarUrl)} alt="" className="w-full h-full object-cover" />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-zinc-600">
                                        <Users className="w-8 h-8" />
                                    </div>
                                )}
                            </div>
                            <div className="flex-1 space-y-2">
                                <input
                                    type="text"
                                    value={avatarUrl}
                                    onChange={(e) => setAvatarUrl(e.target.value)}
                                    placeholder="https://"
                                    className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-white focus:outline-none focus:border-violet-500"
                                />
                                <button
                                    type="button"
                                    onClick={() => setActiveSelector('avatar')}
                                    className="flex items-center gap-2 text-sm text-violet-400 hover:text-violet-300 transition-colors"
                                >
                                    <ImageIcon className="w-4 h-4" />
                                    Select from Library / Upload
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Background URL */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">
                            Background Image
                        </label>
                        <div className="space-y-2 p-3 bg-zinc-800/30 rounded-lg border border-white/5">
                            <div className="w-full h-24 rounded overflow-hidden bg-zinc-800 border-2 border-zinc-700 relative">
                                {backgroundUrl ? (
                                    <img src={getImageUrl(backgroundUrl)} alt="" className="w-full h-full object-cover" />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-zinc-600">
                                        <ImageIcon className="w-8 h-8" />
                                    </div>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                <input
                                    type="text"
                                    value={backgroundUrl}
                                    onChange={(e) => setBackgroundUrl(e.target.value)}
                                    placeholder="https://"
                                    className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-white focus:outline-none focus:border-violet-500"
                                />
                                <button
                                    type="button"
                                    onClick={() => setActiveSelector('background')}
                                    className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm font-medium rounded transition-colors whitespace-nowrap"
                                >
                                    Browse...
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Privacy Level */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-400">
                            Profile Visibility
                        </label>
                        <div className="grid grid-cols-3 gap-2">
                            <button
                                type="button"
                                onClick={() => setPrivacyLevel("public")}
                                className={`flex flex-col items-center gap-2 p-4 rounded-lg border transition-all ${privacyLevel === "public"
                                    ? "bg-green-500/20 border-green-500/50 text-green-400"
                                    : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-white"
                                    }`}
                            >
                                <Globe className="w-5 h-5" />
                                <span className="text-sm font-medium">Public</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setPrivacyLevel("friends")}
                                className={`flex flex-col items-center gap-2 p-4 rounded-lg border transition-all ${privacyLevel === "friends"
                                    ? "bg-blue-500/20 border-blue-500/50 text-blue-400"
                                    : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-white"
                                    }`}
                            >
                                <Users className="w-5 h-5" />
                                <span className="text-sm font-medium">Friends</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setPrivacyLevel("private")}
                                className={`flex flex-col items-center gap-2 p-4 rounded-lg border transition-all ${privacyLevel === "private"
                                    ? "bg-yellow-500/20 border-yellow-500/50 text-yellow-400"
                                    : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-white"
                                    }`}
                            >
                                <Lock className="w-5 h-5" />
                                <span className="text-sm font-medium">Private</span>
                            </button>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-3 pt-4 border-t border-white/10">
                        <button
                            type="submit"
                            disabled={isSaving}
                            className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold rounded-lg transition-all disabled:opacity-50"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                "Save Changes"
                            )}
                        </button>
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-6 py-3 text-zinc-400 hover:text-white font-medium rounded-lg hover:bg-white/5 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            </div>

            {/* Image Selector Modal */}
            {activeSelector && (
                <ImageSelectionModal
                    type={activeSelector}
                    onClose={() => setActiveSelector(null)}
                    onSelect={(url) => {
                        if (activeSelector === 'avatar') setAvatarUrl(url);
                        else if (activeSelector === 'background') setBackgroundUrl(url);
                        setActiveSelector(null);
                    }}
                />
            )}
        </div>
    );
}

import os
import shutil
import sqlite3
import random
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, ttk
import platform
import subprocess
from PIL import Image, ImageTk
import cv2
import string

# ---------- Setup folders ----------
BASE_DIR = Path.cwd()
PROJECT_DIR = BASE_DIR / "Instagram_Clone_files"
PROFILE_DIR = PROJECT_DIR / "profile_pics"
POSTS_DIR = PROJECT_DIR / "posts"
REELS_DIR = PROJECT_DIR / "reels"
THUMBS_DIR = PROJECT_DIR / "thumbnails"

for d in (PROJECT_DIR, PROFILE_DIR, POSTS_DIR, REELS_DIR, THUMBS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------- Database ----------
DB_PATH = PROJECT_DIR / "users.db"

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    display_name TEXT,
    bio TEXT,
    profile_pic TEXT,
    email TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    image_path TEXT,
    caption TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    video_path TEXT,
    caption TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    username TEXT NOT NULL,
    UNIQUE(media_id, media_type, username)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    username TEXT NOT NULL,
    comment TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")

# Add email column if it doesn't exist (for existing databases)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
except sqlite3.OperationalError:
    pass

conn.commit()
print("✅ Database ready!\n")

# ---------- Globals ----------
_image_refs = {"login_logo": None, "profile_photo": None, "post_thumbs": [], "reel_thumbs": []}

# ---------- Utility Functions ----------
def resize_image_keep_aspect(img_path, size):
    """Resize image while maintaining aspect ratio"""
    try:
        img = Image.open(img_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"Error resizing image: {e}")
        return None

def extract_video_thumbnail(video_path, thumb_size=(120, 120)):
    """Extract first frame from video as thumbnail"""
    try:
        if not Path(video_path).exists():
            print(f"Video file not found: {video_path}")
            return None
        
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"Could not extract frame from video: {video_path}")
            return None
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame)
        pil_img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
        
        return pil_img
    except Exception as e:
        print(f"Error extracting video thumbnail: {e}")
        return None

def copy_and_save_media(src_path, dest_dir, prefix="media"):
    """Copy media file to destination with timestamp"""
    try:
        ext = Path(src_path).suffix.lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.mp4', '.mov', '.avi']:
            messagebox.showerror("Error", "Only images (JPG, PNG, BMP, GIF) and videos (MP4, MOV, AVI) are allowed!")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        dest_name = f"{prefix}_{timestamp}{ext}"
        dest_path = dest_dir / dest_name
        shutil.copy(src_path, dest_path)
        return str(dest_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save media: {e}")
        return None

def get_user_profile(username):
    """Retrieve user profile information"""
    try:
        cursor.execute("SELECT display_name, bio, profile_pic FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        if row:
            display_name, bio, profile_pic = row
            return {"display_name": display_name or "", "bio": bio or "", "profile_pic": profile_pic or ""}
        return {"display_name": "", "bio": "", "profile_pic": ""}
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return {"display_name": "", "bio": "", "profile_pic": ""}

def play_video_cross_platform(v_path):
    """Play video in cross-platform way"""
    try:
        if not Path(v_path).exists():
            messagebox.showerror("Error", "Video file not found!")
            return
        
        system = platform.system()
        if system == 'Darwin':
            subprocess.Popen(['open', v_path])
        elif system == 'Windows':
            os.startfile(v_path)
        else:
            subprocess.Popen(['xdg-open', v_path])
    except Exception as e:
        messagebox.showerror("Error", f"Cannot play video: {e}")

# ---------- PASSWORD RECOVERY FUNCTIONS ----------
def generate_temp_password(length=8):
    """Generate a temporary password"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def verify_security_answer(username, answer):
    """Verify user's security answer"""
    try:
        cursor.execute("SELECT username FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            return True
        return False
    except Exception as e:
        print(f"Error verifying: {e}")
        return False

# ---------- Login / Register ----------
def show_login_window():
    """Display login window"""
    global login_window, entry_username, entry_password
    login_window = tk.Tk()
    login_window.title("Instagram Clone - Login")
    login_window.geometry("360x550")
    login_window.config(bg="white")

    try:
        logo_path = BASE_DIR / "instagram_img_logo.png"
        if logo_path.exists():
            logo_img = Image.open(str(logo_path)).resize((80, 80))
            _image_refs["login_logo"] = ImageTk.PhotoImage(logo_img)
            tk.Label(login_window, image=_image_refs["login_logo"], bg="white").pack(pady=8)
    except Exception as e:
        print(f"Logo loading error: {e}")

    tk.Label(login_window, text="Instagram", font=("Helvetica", 28, "bold"), fg="#E1306C", bg="white").pack(pady=(0, 12))

    tk.Label(login_window, text="Username", bg="white").pack()
    entry_username = tk.Entry(login_window, width=32)
    entry_username.pack(pady=5)

    tk.Label(login_window, text="Password", bg="white").pack()
    entry_password = tk.Entry(login_window, width=32, show="*")
    entry_password.pack(pady=5)

    tk.Button(login_window, text="Login", bg="#0095F6", fg="white", width=20, command=login_user).pack(pady=10)
    tk.Button(login_window, text="Create Account", bg="#42B72A", fg="white", width=20, command=register_user).pack(pady=5)
    
    # ⭐ FORGOT PASSWORD BUTTON ⭐
    tk.Button(login_window, text="🔐 Forgot Password?", bg="#FFA500", fg="white", width=20, 
              command=show_forgot_password_window).pack(pady=5)
    
    tk.Label(login_window, text="© 2025 Instagram Clone", font=("Helvetica", 8), fg="gray", bg="white").pack(side="bottom", pady=10)

    login_window.mainloop()

def login_user():
    """Handle user login"""
    try:
        username = entry_username.get().strip()
        password = entry_password.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter username and password")
            return
        
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        if cursor.fetchone():
            login_window.destroy()
            open_dashboard(username)
        else:
            messagebox.showerror("Error", "Invalid credentials")
    except Exception as e:
        messagebox.showerror("Error", f"Login failed: {e}")

def register_user():
    """Handle user registration"""
    try:
        username = entry_username.get().strip()
        password = entry_password.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Error", "Please enter username and password")
            return
        
        if len(password) < 6:
            messagebox.showwarning("Error", "Password must be at least 6 characters long")
            return
        
        # ⭐ Get email during registration ⭐
        email = simpledialog.askstring("Email Required", "Enter your email address:", parent=login_window)
        if not email:
            messagebox.showwarning("Error", "Email is required for password recovery")
            return
        
        cursor.execute("INSERT INTO users (username, password, display_name, bio, profile_pic, email) VALUES (?, ?, ?, ?, ?, ?)",
                       (username, password, username, "", "", email))
        conn.commit()
        messagebox.showinfo("Success", "Account created! Now login with your credentials.")
        entry_username.delete(0, tk.END)
        entry_password.delete(0, tk.END)
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Username already exists")
    except Exception as e:
        messagebox.showerror("Error", f"Registration failed: {e}")

# ⭐ FORGOT PASSWORD WINDOW ⭐
def show_forgot_password_window():
    """Display forgot password window"""
    forgot_window = tk.Toplevel()
    forgot_window.title("Reset Password")
    forgot_window.geometry("400x450")
    forgot_window.config(bg="white")

    tk.Label(forgot_window, text="🔐 Reset Password", font=("Helvetica", 16, "bold"), fg="#E1306C", bg="white").pack(pady=10)

    tk.Label(forgot_window, text="Enter your username:", bg="white", font=("Helvetica", 10)).pack(pady=(10, 0))
    entry_forgot_username = tk.Entry(forgot_window, width=35)
    entry_forgot_username.pack(pady=5)

    tk.Label(forgot_window, text="Enter your email:", bg="white", font=("Helvetica", 10)).pack(pady=(10, 0))
    entry_forgot_email = tk.Entry(forgot_window, width=35)
    entry_forgot_email.pack(pady=5)

    tk.Label(forgot_window, text="Security Question:\nWhat is your favorite color?", bg="white", font=("Helvetica", 10)).pack(pady=(10, 0))
    entry_security_answer = tk.Entry(forgot_window, width=35)
    entry_security_answer.pack(pady=5)

    result_label = tk.Label(forgot_window, text="", bg="white", fg="green", font=("Helvetica", 9), wraplength=350)
    result_label.pack(pady=10)

    def verify_and_reset():
        """Verify user details and reset password"""
        try:
            username = entry_forgot_username.get().strip()
            email = entry_forgot_email.get().strip()
            security_answer = entry_security_answer.get().strip().lower()
            
            if not username or not email or not security_answer:
                messagebox.showwarning("Error", "Please fill in all fields")
                return
            
            # Check if user exists with matching email
            cursor.execute("SELECT email FROM users WHERE username=?", (username,))
            row = cursor.fetchone()
            
            if not row:
                messagebox.showerror("Error", "Username not found")
                return
            
            stored_email = row[0]
            
            if stored_email != email:
                messagebox.showerror("Error", "Email does not match our records")
                return
            
            # Simple verification: just check if security answer is not empty
            # In real app, you'd hash and compare the answer
            if security_answer:
                # Generate temporary password
                temp_password = generate_temp_password()
                
                # Update password in database
                cursor.execute("UPDATE users SET password=? WHERE username=?", (temp_password, username))
                conn.commit()
                
                result_label.config(
                    text=f"✅ Password Reset Successful!\n\n"
                         f"Your temporary password is:\n"
                         f"'{temp_password}'\n\n"
                         f"Please change it after logging in.",
                    fg="green"
                )
                
                # Show the password in a message box
                messagebox.showinfo(
                    "Password Reset",
                    f"Your temporary password is: {temp_password}\n\n"
                    f"Please use this to login and then change your password in profile settings."
                )
                
                forgot_window.after(3000, forgot_window.destroy)
            else:
                messagebox.showerror("Error", "Invalid security answer")
        
        except Exception as e:
            messagebox.showerror("Error", f"Reset failed: {e}")
            print(f"Error: {e}")

    def send_reset_link():
        """Simulate sending reset link via email"""
        try:
            username = entry_forgot_username.get().strip()
            email = entry_forgot_email.get().strip()
            
            if not username or not email:
                messagebox.showwarning("Error", "Please enter username and email")
                return
            
            cursor.execute("SELECT email FROM users WHERE username=?", (username,))
            row = cursor.fetchone()
            
            if not row:
                messagebox.showerror("Error", "Username not found")
                return
            
            if row[0] != email:
                messagebox.showerror("Error", "Email does not match our records")
                return
            
            # In a real app, you would send an email here
            messagebox.showinfo(
                "Reset Link Sent",
                f"A password reset link has been sent to {email}\n\n"
                f"(In a real app, this would send an email. For demo, use security answer instead.)"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    button_frame = tk.Frame(forgot_window, bg="white")
    button_frame.pack(pady=10, fill="x", padx=20)
    
    tk.Button(button_frame, text="Reset Password", bg="#0095F6", fg="white", width=18, 
              command=verify_and_reset).pack(side="left", padx=5)
    
    tk.Button(button_frame, text="Send Reset Link", bg="#42B72A", fg="white", width=18, 
              command=send_reset_link).pack(side="left", padx=5)

    tk.Button(forgot_window, text="← Back to Login", bg="#808080", fg="white", width=30, 
              command=forgot_window.destroy).pack(pady=10)

    info_text = tk.Label(
        forgot_window,
        text="Enter your username and email.\n"
             "Answer the security question to get a temporary password.\n\n"
             "Note: In a real application, you would receive a reset link via email.",
        bg="white",
        fg="gray",
        font=("Helvetica", 8),
        wraplength=380,
        justify="center"
    )
    info_text.pack(pady=10, padx=10)

    forgot_window.mainloop()

# ---------- Dashboard ----------
def open_dashboard(username):
    """Open main dashboard"""
    dashboard = tk.Tk()
    dashboard.title("Instagram Clone - Dashboard")
    dashboard.geometry("650x850")
    dashboard.config(bg="white")

    # Header
    header = tk.Frame(dashboard, bg="white")
    header.pack(fill="x", pady=10)
    
    try:
        logo_path = BASE_DIR / "instagram_img_logo.png"
        if logo_path.exists():
            img = Image.open(str(logo_path)).resize((36, 36))
            logo_photo = ImageTk.PhotoImage(img)
            tk.Label(header, image=logo_photo, bg="white").pack(side="left", padx=10)
            header.logo_photo = logo_photo
    except Exception:
        pass
    
    tk.Label(header, text="Instagram", font=("Helvetica", 20, "bold"), fg="#E1306C", bg="white").pack(side="left")
    tk.Button(header, text="Logout", bg="#E1306C", fg="white", command=lambda: do_logout(dashboard)).pack(side="right", padx=12)

    # PROFILE AREA
    profile_frame = tk.Frame(dashboard, bg="white")
    profile_frame.pack(pady=10, fill="x", padx=20)

    profile_img_label = tk.Label(profile_frame, bg="white")
    profile_img_label.grid(row=0, column=0, rowspan=2, padx=(0, 15))

    display_name_label = tk.Label(profile_frame, text="", font=("Helvetica", 14, "bold"), bg="white")
    display_name_label.grid(row=0, column=1, sticky="w")

    bio_label = tk.Label(profile_frame, text="", font=("Helvetica", 10), bg="white", wraplength=280, justify="left")
    bio_label.grid(row=1, column=1, sticky="w")

    # Stats Row
    stats_frame = tk.Frame(dashboard, bg="white")
    stats_frame.pack(fill="x", padx=20, pady=10)

    posts_stat_label = tk.Label(stats_frame, text="0\nPosts", font=("Helvetica", 11, "bold"), bg="white", width=15)
    followers_stat_label = tk.Label(stats_frame, text="0\nFollowers", font=("Helvetica", 11), bg="white", width=15)
    following_stat_label = tk.Label(stats_frame, text="0\nFollowing", font=("Helvetica", 11), bg="white", width=15)

    posts_stat_label.grid(row=0, column=0, padx=5)
    followers_stat_label.grid(row=0, column=1, padx=5)
    following_stat_label.grid(row=0, column=2, padx=5)

    tk.Button(profile_frame, text="Edit Profile", bg="#0095F6", fg="white",
              command=lambda: open_edit_profile(username, refresh_profile_and_stats)).grid(row=0, column=2, sticky="e", padx=6)

    def refresh_profile_and_stats():
        """Refresh profile information and statistics"""
        try:
            prof = get_user_profile(username)
            display_name = prof["display_name"] or username
            bio_text = prof["bio"] or ""
            img_path = prof["profile_pic"] or ""

            if img_path and Path(img_path).exists():
                img = resize_image_keep_aspect(img_path, (100, 100))
                if img:
                    photo = ImageTk.PhotoImage(img)
                    profile_img_label.config(image=photo, text="")
                    _image_refs["profile_photo"] = photo
                else:
                    profile_img_label.config(image="", text="🧍", font=("Helvetica", 40))
            else:
                profile_img_label.config(image="", text="🧍", font=("Helvetica", 40))

            display_name_label.config(text=display_name)
            bio_label.config(text=bio_text)

            cursor.execute("SELECT COUNT(*) FROM posts WHERE username=?", (username,))
            posts_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM reels WHERE username=?", (username,))
            reels_count = cursor.fetchone()[0]
            
            total_count = posts_count + reels_count
            followers = random.randint(50, 800)
            following = random.randint(10, 500)

            posts_stat_label.config(text=f"{total_count}\nPosts")
            followers_stat_label.config(text=f"{followers}\nFollowers")
            following_stat_label.config(text=f"{following}\nFollowing")
            
            print(f"📊 Stats: Posts={posts_count}, Reels={reels_count}, Total={total_count}")
        except Exception as e:
            print(f"Error refreshing profile: {e}")

    refresh_profile_and_stats()

    tk.Frame(dashboard, bg="#dbdbdb", height=1).pack(fill="x", padx=20, pady=10)

    # Notebook
    notebook = ttk.Notebook(dashboard)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # Posts Tab
    posts_tab = tk.Frame(notebook, bg="white")
    notebook.add(posts_tab, text="📷 Posts")

    # Reels Tab
    reels_tab = tk.Frame(notebook, bg="white")
    notebook.add(reels_tab, text="🎬 Reels")

    # --- POSTS TAB CONTENT ---
    def add_post_flow():
        """Add a new post"""
        try:
            fpath = filedialog.askopenfilename(
                title="Select image",
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
            )
            if not fpath:
                return
            
            caption = simpledialog.askstring("Caption", "Enter caption (optional):") or ""
            saved = copy_and_save_media(fpath, POSTS_DIR, prefix=f"post_{username}")
            
            if saved:
                now = datetime.now().isoformat(timespec="seconds")
                cursor.execute(
                    "INSERT INTO posts (username, image_path, caption, created_at) VALUES (?, ?, ?, ?)",
                    (username, saved, caption, now)
                )
                conn.commit()
                print(f"✅ Post added: {saved}")
                messagebox.showinfo("Posted", "Your image was posted successfully!")
                refresh_profile_and_stats()
                refresh_posts_feed()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to post: {e}")

    tk.Button(posts_tab, text="➕ Add Post", bg="#0095F6", fg="white", width=20, command=add_post_flow).pack(pady=10)

    # Posts Canvas
    posts_canvas = tk.Canvas(posts_tab, bg="white", highlightthickness=0)
    posts_scrollbar = tk.Scrollbar(posts_tab, orient="vertical", command=posts_canvas.yview)
    posts_scrollable_frame = tk.Frame(posts_canvas, bg="white")

    posts_scrollable_frame.bind("<Configure>", lambda e: posts_canvas.configure(scrollregion=posts_canvas.bbox("all")))
    posts_canvas.create_window((0, 0), window=posts_scrollable_frame, anchor="nw")
    posts_canvas.configure(yscrollcommand=posts_scrollbar.set)

    posts_canvas.pack(side="left", fill="both", expand=True)
    posts_scrollbar.pack(side="right", fill="y")

    def refresh_posts_feed():
        """Refresh posts feed display"""
        try:
            for w in posts_scrollable_frame.winfo_children():
                w.destroy()
            _image_refs["post_thumbs"].clear()

            cursor.execute(
                "SELECT id, image_path, caption, created_at FROM posts WHERE username=? ORDER BY id DESC",
                (username,)
            )
            rows = cursor.fetchall()
            print(f"📸 Found {len(rows)} posts")
            
            if not rows:
                tk.Label(posts_scrollable_frame, text="📭 No posts yet. Click 'Add Post' to upload images!",
                        bg="white", fg="gray", font=("Helvetica", 11)).pack(pady=20)
                return

            for post_id, img_path, caption, created_at in rows:
                post_frame = tk.Frame(posts_scrollable_frame, bg="white", bd=1, relief="solid", padx=8, pady=8)
                post_frame.pack(fill="x", pady=6, padx=6)

                if img_path and Path(img_path).exists():
                    thumb_img = resize_image_keep_aspect(img_path, (120, 120))
                    if thumb_img:
                        thumb_photo = ImageTk.PhotoImage(thumb_img)
                        _image_refs["post_thumbs"].append(thumb_photo)
                        thumb_label = tk.Label(post_frame, image=thumb_photo, bg="white", cursor="hand2")
                        thumb_label.grid(row=0, column=0, rowspan=3, padx=6)
                        thumb_label.bind("<Button-1>", lambda e, pid=post_id: open_post_view(pid))
                else:
                    tk.Label(post_frame, text="📸", bg="white", font=("Helvetica", 30)).grid(row=0, column=0, rowspan=3, padx=6)

                tk.Label(post_frame, text=(caption or "<No caption>"), bg="white", 
                        font=("Helvetica", 11), anchor="w", justify="left", wraplength=330).grid(row=0, column=1, sticky="w")
                tk.Label(post_frame, text=f"📅 {created_at}", bg="white", fg="gray", 
                        font=("Helvetica", 8)).grid(row=1, column=1, sticky="w", pady=(4, 0))

                cursor.execute(
                    "SELECT COUNT(*) FROM likes WHERE media_id=? AND media_type=?",
                    (post_id, 'post')
                )
                like_count = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                    (post_id, 'post', username)
                )
                is_liked = cursor.fetchone() is not None

                def make_toggle_like(pid):
                    def toggle_like():
                        try:
                            cursor.execute(
                                "SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                (pid, 'post', username)
                            )
                            if cursor.fetchone():
                                cursor.execute(
                                    "DELETE FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                    (pid, 'post', username)
                                )
                            else:
                                cursor.execute(
                                    "INSERT INTO likes (media_id, media_type, username) VALUES (?, ?, ?)",
                                    (pid, 'post', username)
                                )
                            conn.commit()
                            refresh_posts_feed()
                        except Exception as e:
                            messagebox.showerror("Error", f"Like failed: {e}")
                    return toggle_like

                like_btn = tk.Button(post_frame, text=f"❤️ {like_count}", bg="white", 
                                    fg=("red" if is_liked else "gray"), bd=0, command=make_toggle_like(post_id))
                like_btn.grid(row=2, column=1, sticky="w", pady=2)

                def make_add_comment(pid):
                    def add_comment_dialog():
                        try:
                            comment_text = simpledialog.askstring("Add Comment", "Write your comment:", parent=dashboard)
                            if comment_text:
                                now = datetime.now().isoformat(timespec="seconds")
                                cursor.execute(
                                    "INSERT INTO comments (media_id, media_type, username, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                                    (pid, 'post', username, comment_text, now)
                                )
                                conn.commit()
                                messagebox.showinfo("Success", "Comment added!")
                                refresh_posts_feed()
                        except Exception as e:
                            messagebox.showerror("Error", f"Comment failed: {e}")
                    return add_comment_dialog

                tk.Button(post_frame, text="💬 Comment", bg="white", fg="#0095F6", bd=0, 
                         command=make_add_comment(post_id)).grid(row=2, column=1, sticky="e", pady=2)

                def make_delete_post(pid, ppath):
                    def delete_post():
                        try:
                            if messagebox.askyesno("Delete", "Delete this post permanently?"):
                                cursor.execute("DELETE FROM posts WHERE id=?", (pid,))
                                cursor.execute("DELETE FROM likes WHERE media_id=? AND media_type=?", (pid, 'post'))
                                cursor.execute("DELETE FROM comments WHERE media_id=? AND media_type=?", (pid, 'post'))
                                conn.commit()
                                
                                if ppath and Path(ppath).exists():
                                    try:
                                        Path(ppath).unlink()
                                    except Exception:
                                        pass
                                
                                refresh_profile_and_stats()
                                refresh_posts_feed()
                        except Exception as e:
                            messagebox.showerror("Error", f"Delete failed: {e}")
                    return delete_post

                tk.Button(post_frame, text="🗑️ Delete", bg="#E1306C", fg="white", 
                         command=make_delete_post(post_id, img_path)).grid(row=0, column=2, padx=8)
        except Exception as e:
            print(f"Error refreshing posts feed: {e}")

    # --- REELS TAB CONTENT ---
    def add_reel_flow():
        """Add a new reel"""
        try:
            vpath = filedialog.askopenfilename(
                title="Select Video",
                filetypes=[("Video files", "*.mp4;*.mov;*.avi")]
            )
            if not vpath:
                return
            
            caption = simpledialog.askstring("Caption", "Enter caption (optional):") or ""
            saved = copy_and_save_media(vpath, REELS_DIR, prefix=f"reel_{username}")
            
            if saved:
                now = datetime.now().isoformat(timespec="seconds")
                cursor.execute(
                    "INSERT INTO reels (username, video_path, caption, created_at) VALUES (?, ?, ?, ?)",
                    (username, saved, caption, now)
                )
                conn.commit()
                print(f"✅ Reel added: {saved}")
                messagebox.showinfo("Posted", "Your reel was posted successfully!")
                refresh_profile_and_stats()
                refresh_reels_feed()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to post reel: {e}")
            print(f"❌ Reel error: {e}")

    tk.Button(reels_tab, text="➕ Add Reel", bg="#A70C4A", fg="white", width=20, command=add_reel_flow).pack(pady=10)

    # Reels Canvas
    reels_canvas = tk.Canvas(reels_tab, bg="white", highlightthickness=0)
    reels_scrollbar = tk.Scrollbar(reels_tab, orient="vertical", command=reels_canvas.yview)
    reels_scrollable_frame = tk.Frame(reels_canvas, bg="white")

    reels_scrollable_frame.bind("<Configure>", lambda e: reels_canvas.configure(scrollregion=reels_canvas.bbox("all")))
    reels_canvas.create_window((0, 0), window=reels_scrollable_frame, anchor="nw")
    reels_canvas.configure(yscrollcommand=reels_scrollbar.set)

    reels_canvas.pack(side="left", fill="both", expand=True)
    reels_scrollbar.pack(side="right", fill="y")

    def refresh_reels_feed():
        """Refresh reels feed display"""
        try:
            for w in reels_scrollable_frame.winfo_children():
                w.destroy()
            _image_refs["reel_thumbs"].clear()

            cursor.execute(
                "SELECT id, video_path, caption, created_at FROM reels WHERE username=? ORDER BY id DESC",
                (username,)
            )
            rows = cursor.fetchall()
            print(f"🎬 Found {len(rows)} reels")
            
            if not rows:
                tk.Label(reels_scrollable_frame, text="📭 No reels yet. Click 'Add Reel' to upload videos!",
                        bg="white", fg="gray", font=("Helvetica", 11)).pack(pady=20)
                return

            for media_id, video_path, caption, created_at in rows:
                reels_frame = tk.Frame(reels_scrollable_frame, bg="white", bd=1, relief="solid", padx=8, pady=8)
                reels_frame.pack(fill="x", pady=6, padx=6)

                if video_path and Path(video_path).exists():
                    thumb_img = extract_video_thumbnail(video_path, thumb_size=(120, 120))
                    if thumb_img:
                        thumb_photo = ImageTk.PhotoImage(thumb_img)
                        _image_refs["reel_thumbs"].append(thumb_photo)
                        thumb_label = tk.Label(reels_frame, image=thumb_photo, bg="white", cursor="hand2")
                        thumb_label.grid(row=0, column=0, rowspan=3, padx=6)
                        thumb_label.bind("<Button-1>", lambda e, rid=media_id: open_reel_view(rid))
                    else:
                        play_button = tk.Button(
                            reels_frame,
                            text="▶\nPLAY",
                            font=("Helvetica", 14, "bold"),
                            bg="#A70C4A",
                            fg="white",
                            width=10,
                            height=4,
                            command=lambda vp=video_path, rid=media_id: open_reel_view(rid)
                        )
                        play_button.grid(row=0, column=0, rowspan=3, padx=6, pady=6)
                else:
                    tk.Label(reels_frame, text="🎬", bg="white", font=("Helvetica", 30)).grid(row=0, column=0, rowspan=3, padx=6)

                tk.Label(reels_frame, text=(caption or "<No caption>"), bg="white",
                        font=("Helvetica", 11), anchor="w", justify="left", wraplength=330).grid(row=0, column=1, sticky="w")
                tk.Label(reels_frame, text=f"📅 {created_at}", bg="white", fg="gray",
                        font=("Helvetica", 8)).grid(row=1, column=1, sticky="w", pady=(4, 0))

                cursor.execute(
                    "SELECT COUNT(*) FROM likes WHERE media_id=? AND media_type=?",
                    (media_id, 'reel')
                )
                like_count = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                    (media_id, 'reel', username)
                )
                is_liked = cursor.fetchone() is not None

                def make_toggle_like_reel(rid):
                    def toggle_like():
                        try:
                            cursor.execute(
                                "SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                (rid, 'reel', username)
                            )
                            if cursor.fetchone():
                                cursor.execute(
                                    "DELETE FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                    (rid, 'reel', username)
                                )
                            else:
                                cursor.execute(
                                    "INSERT INTO likes (media_id, media_type, username) VALUES (?, ?, ?)",
                                    (rid, 'reel', username)
                                )
                            conn.commit()
                            refresh_reels_feed()
                        except Exception as e:
                            messagebox.showerror("Error", f"Like failed: {e}")
                    return toggle_like

                like_btn = tk.Button(reels_frame, text=f"❤️ {like_count}", bg="white",
                                    fg=("red" if is_liked else "gray"), bd=0, command=make_toggle_like_reel(media_id))
                like_btn.grid(row=2, column=1, sticky="w", pady=2)

                def make_add_comment_reel(rid):
                    def add_comment_dialog():
                        try:
                            comment_text = simpledialog.askstring("Add Comment", "Write your comment:", parent=dashboard)
                            if comment_text:
                                now = datetime.now().isoformat(timespec="seconds")
                                cursor.execute(
                                    "INSERT INTO comments (media_id, media_type, username, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                                    (rid, 'reel', username, comment_text, now)
                                )
                                conn.commit()
                                messagebox.showinfo("Success", "Comment added!")
                                refresh_reels_feed()
                        except Exception as e:
                            messagebox.showerror("Error", f"Comment failed: {e}")
                    return add_comment_dialog

                tk.Button(reels_frame, text="💬 Comment", bg="white", fg="#0095F6", bd=0,
                         command=make_add_comment_reel(media_id)).grid(row=2, column=1, sticky="e", pady=2)

                def make_delete_reel(rid, v_path):
                    def delete_reel():
                        try:
                            if messagebox.askyesno("Delete", "Delete this reel permanently?"):
                                cursor.execute("DELETE FROM reels WHERE id=?", (rid,))
                                cursor.execute("DELETE FROM likes WHERE media_id=? AND media_type=?", (rid, 'reel'))
                                cursor.execute("DELETE FROM comments WHERE media_id=? AND media_type=?", (rid, 'reel'))
                                conn.commit()
                                
                                if v_path and Path(v_path).exists():
                                    try:
                                        Path(v_path).unlink()
                                    except Exception:
                                        pass
                                
                                refresh_profile_and_stats()
                                refresh_reels_feed()
                        except Exception as e:
                            messagebox.showerror("Error", f"Delete failed: {e}")
                    return delete_reel

                tk.Button(reels_frame, text="🗑️ Delete", bg="#E1306C", fg="white",
                         command=make_delete_reel(media_id, video_path)).grid(row=0, column=2, padx=8)
        except Exception as e:
            print(f"Error refreshing reels feed: {e}")

    # Open full post view
    def open_post_view(post_id):
        """Open detailed post view"""
        try:
            top = tk.Toplevel()
            top.title("View Post")
            top.geometry("550x750")
            top.config(bg="white")

            cursor.execute("SELECT username, image_path, caption, created_at FROM posts WHERE id=?", (post_id,))
            row = cursor.fetchone()
            
            if not row:
                tk.Label(top, text="❌ Post not found", bg="white", fg="red").pack(pady=20)
                return
            
            post_user, img_path, cap, dt = row

            if img_path and Path(img_path).exists():
                img = resize_image_keep_aspect(img_path, (500, 500))
                if img:
                    ph = ImageTk.PhotoImage(img)
                    tk.Label(top, image=ph, bg="white").pack(pady=8)
                    top.photo_ref = ph

            tk.Label(top, text=f"@{post_user}", font=("Helvetica", 12, "bold"), bg="white").pack()
            tk.Label(top, text=cap or "", bg="white", wraplength=500).pack(pady=4)
            tk.Label(top, text=f"📅 {dt}", font=("Helvetica", 9), bg="white", fg="gray").pack(pady=(0, 8))

            cursor.execute("SELECT COUNT(*) FROM likes WHERE media_id=? AND media_type=?", (post_id, 'post'))
            like_count = cursor.fetchone()[0]
            cursor.execute("SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?", 
                          (post_id, 'post', username))
            is_liked = cursor.fetchone() is not None

            def toggle_like_in_view():
                try:
                    cursor.execute("SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                  (post_id, 'post', username))
                    if cursor.fetchone():
                        cursor.execute("DELETE FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                      (post_id, 'post', username))
                    else:
                        cursor.execute("INSERT INTO likes (media_id, media_type, username) VALUES (?, ?, ?)",
                                      (post_id, 'post', username))
                    conn.commit()
                    refresh_like_label()
                    refresh_posts_feed()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed: {e}")

            like_frame = tk.Frame(top, bg="white")
            like_frame.pack(fill="x", padx=10, pady=5)
            like_label = tk.Label(like_frame, text=f"❤️ {like_count}", bg="white", 
                                 fg=("red" if is_liked else "gray"), font=("Helvetica", 11, "bold"))
            like_label.pack(side="left", padx=5)
            tk.Button(like_frame, text="Toggle Like", bg="#f0f0f0", command=toggle_like_in_view).pack(side="left", padx=5)

            tk.Label(top, text="Comments:", bg="white", font=("Helvetica", 12, "bold")).pack(pady=(10, 0))
            
            comments_canvas = tk.Canvas(top, bg="white", highlightthickness=0)
            comments_scrollbar = tk.Scrollbar(top, orient="vertical", command=comments_canvas.yview)
            comments_container = tk.Frame(comments_canvas, bg="white")

            comments_container.bind("<Configure>", lambda e: comments_canvas.configure(scrollregion=comments_canvas.bbox("all")))
            comments_canvas.create_window((0, 0), window=comments_container, anchor="nw")
            comments_canvas.configure(yscrollcommand=comments_scrollbar.set)

            comments_canvas.pack(side="left", fill="both", expand=True, padx=10)
            comments_scrollbar.pack(side="right", fill="y")

            def refresh_comments():
                for w in comments_container.winfo_children():
                    w.destroy()
                cursor.execute(
                    "SELECT username, comment, created_at FROM comments WHERE media_id=? AND media_type=? ORDER BY id ASC",
                    (post_id, 'post')
                )
                for cu, ctext, ctime in cursor.fetchall():
                    tk.Label(comments_container, text=f"👤 {cu}: {ctext}", bg="white", anchor="w", 
                            justify="left", wraplength=450, font=("Helvetica", 9)).pack(anchor="w", pady=3, fill="x", padx=5)

            def add_comment_in_view():
                c = simpledialog.askstring("Add Comment", "Write your comment:", parent=top)
                if c:
                    try:
                        now = datetime.now().isoformat(timespec="seconds")
                        cursor.execute(
                            "INSERT INTO comments (media_id, media_type, username, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                            (post_id, 'post', username, c, now)
                        )
                        conn.commit()
                        refresh_comments()
                        messagebox.showinfo("Success", "Comment added!")
                        refresh_posts_feed()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed: {e}")

            tk.Button(top, text="💬 Add Comment", bg="#0095F6", fg="white", command=add_comment_in_view).pack(pady=10)

            def refresh_like_label():
                cursor.execute("SELECT COUNT(*) FROM likes WHERE media_id=? AND media_type=?", (post_id, 'post'))
                lc = cursor.fetchone()[0]
                cursor.execute("SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                              (post_id, 'post', username))
                liked_now = cursor.fetchone() is not None
                like_label.config(text=f"❤️ {lc}", fg=("red" if liked_now else "gray"))

            refresh_comments()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open post: {e}")

    # Open full reel view
    def open_reel_view(reel_id):
        """Open detailed reel view"""
        try:
            top = tk.Toplevel()
            top.title("View Reel")
            top.geometry("550x750")
            top.config(bg="white")

            cursor.execute("SELECT username, video_path, caption, created_at FROM reels WHERE id=?", (reel_id,))
            row = cursor.fetchone()
            
            if not row:
                tk.Label(top, text="❌ Reel not found", bg="white", fg="red").pack(pady=20)
                return
            
            reel_user, v_path, cap, dt = row

            if v_path and Path(v_path).exists():
                thumb_img = extract_video_thumbnail(v_path, thumb_size=(400, 400))
                if thumb_img:
                    ph = ImageTk.PhotoImage(thumb_img)
                    tk.Label(top, image=ph, bg="white").pack(pady=8)
                    top.photo_ref = ph
                
                tk.Button(top, text="▶️ PLAY VIDEO", font=("Helvetica", 16, "bold"),
                         bg="#A70C4A", fg="white", width=20, height=2,
                         command=lambda: play_video_cross_platform(v_path)).pack(pady=10)
            else:
                tk.Label(top, text="❌ Video file missing!", bg="white", fg="red").pack(pady=20)

            tk.Label(top, text=f"@{reel_user}", font=("Helvetica", 12, "bold"), bg="white").pack()
            tk.Label(top, text=cap or "", bg="white", wraplength=500).pack(pady=4)
            tk.Label(top, text=f"📅 {dt}", font=("Helvetica", 9), bg="white", fg="gray").pack(pady=(0, 8))

            cursor.execute("SELECT COUNT(*) FROM likes WHERE media_id=? AND media_type=?", (reel_id, 'reel'))
            like_count = cursor.fetchone()[0]
            cursor.execute("SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                          (reel_id, 'reel', username))
            is_liked = cursor.fetchone() is not None

            def toggle_like_in_view():
                try:
                    cursor.execute("SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                  (reel_id, 'reel', username))
                    if cursor.fetchone():
                        cursor.execute("DELETE FROM likes WHERE media_id=? AND media_type=? AND username=?",
                                      (reel_id, 'reel', username))
                    else:
                        cursor.execute("INSERT INTO likes (media_id, media_type, username) VALUES (?, ?, ?)",
                                      (reel_id, 'reel', username))
                    conn.commit()
                    refresh_like_label()
                    refresh_reels_feed()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed: {e}")

            like_frame = tk.Frame(top, bg="white")
            like_frame.pack(fill="x", padx=10, pady=5)
            like_label = tk.Label(like_frame, text=f"❤️ {like_count}", bg="white",
                                 fg=("red" if is_liked else "gray"), font=("Helvetica", 11, "bold"))
            like_label.pack(side="left", padx=5)
            tk.Button(like_frame, text="Toggle Like", bg="#f0f0f0", command=toggle_like_in_view).pack(side="left", padx=5)

            tk.Label(top, text="Comments:", bg="white", font=("Helvetica", 12, "bold")).pack(pady=(10, 0))
            
            comments_canvas = tk.Canvas(top, bg="white", highlightthickness=0)
            comments_scrollbar = tk.Scrollbar(top, orient="vertical", command=comments_canvas.yview)
            comments_container = tk.Frame(comments_canvas, bg="white")

            comments_container.bind("<Configure>", lambda e: comments_canvas.configure(scrollregion=comments_canvas.bbox("all")))
            comments_canvas.create_window((0, 0), window=comments_container, anchor="nw")
            comments_canvas.configure(yscrollcommand=comments_scrollbar.set)

            comments_canvas.pack(side="left", fill="both", expand=True, padx=10)
            comments_scrollbar.pack(side="right", fill="y")

            def refresh_comments():
                for w in comments_container.winfo_children():
                    w.destroy()
                cursor.execute(
                    "SELECT username, comment, created_at FROM comments WHERE media_id=? AND media_type=? ORDER BY id ASC",
                    (reel_id, 'reel')
                )
                for cu, ctext, ctime in cursor.fetchall():
                    tk.Label(comments_container, text=f"👤 {cu}: {ctext}", bg="white", anchor="w",
                            justify="left", wraplength=450, font=("Helvetica", 9)).pack(anchor="w", pady=3, fill="x", padx=5)

            def add_comment_in_view():
                c = simpledialog.askstring("Add Comment", "Write your comment:", parent=top)
                if c:
                    try:
                        now = datetime.now().isoformat(timespec="seconds")
                        cursor.execute(
                            "INSERT INTO comments (media_id, media_type, username, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                            (reel_id, 'reel', username, c, now)
                        )
                        conn.commit()
                        refresh_comments()
                        messagebox.showinfo("Success", "Comment added!")
                        refresh_reels_feed()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed: {e}")

            tk.Button(top, text="💬 Add Comment", bg="#A70C4A", fg="white", command=add_comment_in_view).pack(pady=10)

            def refresh_like_label():
                cursor.execute("SELECT COUNT(*) FROM likes WHERE media_id=? AND media_type=?", (reel_id, 'reel'))
                lc = cursor.fetchone()[0]
                cursor.execute("SELECT 1 FROM likes WHERE media_id=? AND media_type=? AND username=?",
                              (reel_id, 'reel', username))
                liked_now = cursor.fetchone() is not None
                like_label.config(text=f"❤️ {lc}", fg=("red" if liked_now else "gray"))

            refresh_comments()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open reel: {e}")

    # Initial load
    print("\n🔄 Loading initial feeds...")
    refresh_posts_feed()
    refresh_reels_feed()

    # Footer
    tk.Label(dashboard, text=f"👤 Logged in as: {username}", bg="white", fg="gray", 
            font=("Helvetica", 9)).pack(side="bottom", pady=8)

    dashboard.mainloop()

def do_logout(win):
    """Logout and return to login screen"""
    win.destroy()
    show_login_window()

# ---------- Edit Profile ----------
def open_edit_profile(username, refresh_callback):
    """Open edit profile window"""
    try:
        top = tk.Toplevel()
        top.title("Edit Profile")
        top.geometry("450x450")
        top.config(bg="white")

        prof = get_user_profile(username)
        current_pic = prof["profile_pic"] or ""

        tk.Label(top, text="✏️ Edit Profile", font=("Helvetica", 16, "bold"), bg="white").pack(pady=10)

        photo_label = tk.Label(top, bg="white")
        photo_label.pack(pady=10)

        def refresh_pic_display():
            if current_pic and Path(current_pic).exists():
                img = resize_image_keep_aspect(current_pic, (120, 120))
                if img:
                    ph = ImageTk.PhotoImage(img)
                    photo_label.config(image=ph, text="")
                    top.photo_ref = ph
                else:
                    photo_label.config(image="", text="🧍", font=("Helvetica", 40))
            else:
                photo_label.config(image="", text="🧍", font=("Helvetica", 40))

        refresh_pic_display()

        def change_pic():
            nonlocal current_pic
            f = filedialog.askopenfilename(
                title="Select profile image",
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
            )
            if not f:
                return
            saved = copy_and_save_media(f, PROFILE_DIR, prefix=f"profile_{username}")
            if saved:
                current_pic = saved
                refresh_pic_display()

        tk.Button(top, text="📸 Change Picture", bg="#0095F6", fg="white", 
                 width=25, command=change_pic).pack(pady=8)

        tk.Label(top, text="Display Name", bg="white", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        ent_name = tk.Entry(top, width=40, font=("Helvetica", 11))
        ent_name.insert(0, prof["display_name"])
        ent_name.pack(padx=20, pady=5)

        tk.Label(top, text="Bio", bg="white", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        txt_bio = tk.Text(top, height=5, width=40, font=("Helvetica", 10))
        txt_bio.insert("1.0", prof["bio"])
        txt_bio.pack(padx=20, pady=5)

        def save_profile():
            try:
                new_name = ent_name.get().strip() or username
                new_bio = txt_bio.get("1.0", "end").strip()
                cursor.execute(
                    "UPDATE users SET display_name=?, bio=?, profile_pic=? WHERE username=?",
                    (new_name, new_bio, current_pic, username)
                )
                conn.commit()
                messagebox.showinfo("Success", "✅ Profile updated successfully!")
                refresh_callback()
                top.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save profile: {e}")

        tk.Button(top, text="💾 Save Changes", bg="#42B72A", fg="white", 
                 width=25, command=save_profile).pack(pady=15)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open edit profile: {e}")

# ---------- Run ----------
if __name__ == "__main__":
    show_login_window()
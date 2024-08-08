import os
import requests
from urllib.parse import urlparse
from tkinter import Tk, Button, Label, filedialog, messagebox, Frame, ttk
from tkinter.font import Font
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
import threading
import hashlib

# Function to load cookies from a file
def load_cookies(file_path):
    cookies = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            for line in file:
                if '=' in line:
                    name, value = line.strip().split('=', 1)
                    cookies[name] = value
    return cookies

# Function to generate a unique file name based on the image URL
def generate_file_name(url):
    parsed_url = urlparse(url)
    url_path = parsed_url.path  # Remove query parameters
    return hashlib.md5(url_path.encode('utf-8')).hexdigest() + os.path.splitext(url_path)[1]

# Download image function with cookies
def download_image(url, folder, cookies):
    file_name = generate_file_name(url)
    file_path = os.path.join(folder, file_name)
    
    if os.path.exists(file_path):
        return file_path

    try:
        response = requests.get(url, stream=True, cookies=cookies, verify=False)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return file_path
        else:
            return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

# Process HTML function
def process_html(file_path, output_path, progress_callback, cookies):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    soup = BeautifulSoup(content, "html.parser")
    img_folder = os.path.join(os.path.dirname(output_path), "img")
    os.makedirs(img_folder, exist_ok=True)

    # Extract necessary elements
    items = []
    img_tags = soup.find_all('img')
    total_imgs = len(img_tags)
    
    for li in soup.select("ul.chatContent > li"):
        img_tag = li.select_one("div > img")
        avatar_tag = li.select_one("img.titleImg")
        time_tag = li.select_one("p.timeInfo > span.time")
        text_tag = li.select_one("div > p:nth-of-type(2)")

        if img_tag and avatar_tag and time_tag and text_tag:
            img_url = img_tag["src"]
            avatar_url = avatar_tag["src"]
            time_info = time_tag.text
            text_content = text_tag.text.strip()
            
            # Extract the required text part from p[2]
            if '**' in text_content:
                text_content = text_content.split('**')[1].strip()

            # Download images and update URLs
            local_img_url = download_image(img_url, img_folder, cookies)
            local_avatar_url = download_image(avatar_url, img_folder, cookies)
            if local_img_url and local_avatar_url:
                local_img_url = os.path.relpath(local_img_url, os.path.dirname(output_path))
                local_avatar_url = os.path.relpath(local_avatar_url, os.path.dirname(output_path))

                # Collect all necessary information into a dictionary
                item = {
                    "img_url": local_img_url,
                    "avatar_url": local_avatar_url,
                    "time_info": time_info,
                    "text_content": text_content
                }
                items.append(item)
        
        progress_callback(len(items), total_imgs)

    # Create new HTML content
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Waterfall Layout</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
            }}
            .container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: space-around;
            }}
            .card {{
                width: 300px;
                margin: 15px;
                border: 1px solid #ccc;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            .card img.main-img {{
                width: 100%;
                height: auto;
            }}
            .card-content {{
                padding: 15px;
            }}
            .avatar-time {{
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }}
            .avatar-time .avatar {{
                width: 15px;
                height: 15px;
                border-radius: 50%;
                vertical-align: middle;
                margin-right: 10px;
            }}
            .time {{
                color: gray;
                font-size: 12px;
            }}
            .text-content {{
                margin-top: 10px;
                word-break: break-word;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {}
        </div>
    </body>
    </html>
    """

    card_template = """
    <div class="card">
        <img class="main-img" src="{img_url}" alt="Image">
        <div class="card-content">
            <div class="avatar-time">
                <img class="avatar" src="{avatar_url}" alt="Avatar">
                <span class="time">{time_info}</span>
            </div>
            <div class="text-content">{text_content}</div>
        </div>
    </div>
    """

    cards_html = "".join(card_template.format(
        img_url=item["img_url"],
        avatar_url=item["avatar_url"],
        time_info=item["time_info"],
        text_content=item["text_content"]
    ) for item in items)

    final_html = html_template.format(cards_html)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(final_html)

def select_file():
    file_path = filedialog.askopenfilename(
        title="Select HTML File",
        filetypes=(("HTML Files", "*.html"), ("All Files", "*.*"))
    )
    if file_path:
        process_button.config(state="normal")
        file_label.config(text=os.path.basename(file_path))
        global selected_file_path
        selected_file_path = file_path
    else:
        process_button.config(state="disabled")
        file_label.config(text="No file selected")

def save_file():
    output_path = filedialog.asksaveasfilename(
        title="Save Processed File",
        defaultextension=".html",
        filetypes=(("HTML Files", "*.html"), ("All Files", "*.*"))
    )
    if output_path:
        progress_bar["value"] = 0
        threading.Thread(target=process_html_thread, args=(selected_file_path, output_path)).start()
    else:
        messagebox.showwarning("No save location selected", "No save location was selected. Exiting.")

def process_html_thread(file_path, output_path):
    def update_progress(current, total):
        progress_bar["value"] = (current / total) * 100
        progress_label.config(text=f"Progress: {current}/{total} images")

    try:
        cookies_file_path = os.path.join(os.path.abspath(os.sep), 'cookies.txt')
        cookies = load_cookies(cookies_file_path)
        process_html(file_path, output_path, update_progress, cookies)
        messagebox.showinfo("Success", f"文件处理并保存到 : {output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"处理文件时出错: {e}")

# Create the Tkinter root window
root = Tk()
root.title("HTML Processor")

# Set window size
root.geometry("500x400")
root.title("HTML Processor")
root.minsize(width=500, height=400)
root.maxsize(width=500, height=400)
script_dir = os.path.dirname(__file__)
icon_path = os.path.join(script_dir, 'icon.ico')
root.iconbitmap(icon_path)

# Custom font
custom_font = Font(family="Helvetica", size=12)

# Create a frame for better layout
frame = Frame(root, padx=20, pady=20)
frame.pack(expand=True)

# Create and place the widgets
select_button = Button(frame, text="选择需要处理的HTML文件", command=select_file, font=custom_font, bg="#4CAF50", fg="white", padx=10, pady=5)
select_button.pack(pady=10)

file_label = Label(frame, text="请选择文件", font=custom_font)
file_label.pack(pady=10)

process_button = Button(frame, text="保存文件", state="disabled", command=save_file, font=custom_font, bg="#008CBA", fg="white", padx=10, pady=5)
process_button.pack(pady=10)

progress_label = Label(frame, text="Progress: 0/0 images", font=custom_font)
progress_label.pack(pady=10)

progress_bar = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(pady=10)

# Start the Tkinter event loop
root.mainloop()

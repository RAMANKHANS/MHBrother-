import os
# Pydroid 3 / Android par Window aur Touch providers ki crash rokne ke liye
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_AUDIO'] = 'sdl2'

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserIconView
from kivy.properties import ListProperty
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from datetime import datetime
import requests
import json
import random

# Safe check for Window initialization to avoid NoneType errors
if Window:
    Window.softinput_mode = "below_target"

# --- CONFIG CONSTANTS ---
USERS_FIREBASE_URL = "https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/users.json"
FIREBASE_URL = "https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/inventory.json"
FIREBASE_META_URL = "https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/metadata.json"
PRIMARY_ADMIN_MOBILE = "9664118527"


# --- HELPER FUNCTION TO CHECK ADMIN ---
def is_user_admin(mobile, users_data=None):
    if str(mobile).strip() == PRIMARY_ADMIN_MOBILE:
        return True
    if users_data and isinstance(users_data, dict):
        for u_key, u_val in users_data.items():
            if isinstance(u_val, dict) and str(u_val.get("mobile", "")).strip() == str(mobile).strip():
                return bool(u_val.get("is_admin", False))
    return False


# --- DETAILS SCREEN ---
class DetailsScreen(Screen):
    def load_details(self, row, columns):
        layout = self.ids.details_layout
        layout.clear_widgets()

        for col, val in zip(columns, row):
            if col.lower() == 'id': 
                continue

            if col.lower() == 'images' and isinstance(val, list) and val:
                img_header = Label(
                    text="Vehicle Images:",
                    bold=True,
                    color=(0.1, 0.2, 0.4, 1),
                    font_size='16sp',
                    size_hint_y=None,
                    height=dp(30),
                    halign='left'
                )
                img_header.bind(size=lambda s, w: setattr(s, 'text_size', s.size))
                layout.add_widget(img_header)

                from kivy.uix.scrollview import ScrollView
                from kivy.uix.gridlayout import GridLayout

                scroll = ScrollView(
                    size_hint_y=None,
                    height=dp(100),
                    do_scroll_x=True,
                    do_scroll_y=False
                )
                
                preview_grid = GridLayout(
                    rows=1,
                    spacing=dp(10),
                    size_hint_x=None,
                    width=dp(100),
                    padding=dp(5)
                )
                
                for img_path in val:
                    if os.path.exists(str(img_path)):
                        item_box = BoxLayout(
                            orientation='vertical',
                            size_hint=(None, None),
                            size=(dp(90), dp(90)),
                            spacing=dp(2)
                        )
                        
                        img_btn = Button(
                            background_normal=str(img_path),
                            background_down=str(img_path),
                            size_hint=(1, None),
                            height=dp(90)
                        )
                        img_btn.bind(on_release=lambda btn, p=str(img_path): self.show_full_image(p))
                        
                        item_box.add_widget(img_btn)
                        preview_grid.add_widget(item_box)
                
                scroll.add_widget(preview_grid)
                layout.add_widget(scroll)
                continue

            row_box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(55),
                padding=(dp(12), 0),
                spacing=dp(10)
            )

            left = Label(
                text=str(col).replace("_", " ").title(),
                color=(0.3, 0.3, 0.3, 1),
                font_size='15sp',
                bold=True,
                halign='left',
                valign='middle',
                text_size=(dp(140), None),
                size_hint_x=None,
                width=dp(140)
            )

            right = Label(
                text=':  ' + str(val if val else "-"),
                bold=True,
                color=(0.1, 0.1, 0.1, 1),
                font_size='15sp',
                halign='left',
                valign='middle',
                text_size=(dp(240), None)
            )

            row_box.add_widget(left)
            row_box.add_widget(right)
            layout.add_widget(row_box)

    def show_full_image(self, image_path):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        full_img = Image(
            source=image_path,
            allow_stretch=True,
            keep_ratio=True
        )
        
        close_btn = Button(
            text="Close", 
            size_hint_y=None, 
            height=dp(45),
            background_color=(0, 0, 0, 0), 
            background_normal='', 
            bold=True,
            color=(1, 1, 1, 1)
        )
        with close_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.2, 0.6, 0.8, 1)
            close_btn.rect = RoundedRectangle(pos=close_btn.pos, size=close_btn.size, radius=[15, 15, 15, 15])
        close_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
        
        content.add_widget(full_img)
        content.add_widget(close_btn)
        
        popup = Popup(title="Full Image View", content=content, size_hint=(0.9, 0.9))
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def go_back(self, instance=None):
        self.manager.current = 'view'


# --- MANAGE USERS SCREEN (ADMIN) ---
class ManageUsersScreen(Screen):
    def on_enter(self):
        self.load_users()

    def load_users(self):
        layout = self.ids.users_layout
        layout.clear_widgets()

        try:
            response = requests.get(USERS_FIREBASE_URL)
            if response.status_code == 200 and response.json():
                users_data = response.json()
                total_count = len(users_data)
                active_count = sum(1 for u in users_data.values() if isinstance(u, dict) and u.get("is_active"))
                
                self.ids.users_count_label.text = f"Total: {total_count} | Active: {active_count} | Inactive: {total_count - active_count}"

                for user_key, u_info in users_data.items():
                    if not isinstance(u_info, dict):
                        continue
                    
                    name = u_info.get("name", "Unknown")
                    mobile = u_info.get("mobile", "")
                    email = u_info.get("email", "No Email")
                    is_active = u_info.get("is_active", False)
                    is_admin = u_info.get("is_admin", False) or (mobile == PRIMARY_ADMIN_MOBILE)

                    card_box = BoxLayout(
                        orientation='vertical',
                        size_hint_y=None,
                        height=dp(110),
                        padding=dp(10),
                        spacing=dp(4)
                    )
                    with card_box.canvas.before:
                        from kivy.graphics import Color, RoundedRectangle
                        if is_admin:
                            Color(0.85, 0.92, 1, 1) # Light blue for admin
                        elif is_active:
                            Color(0.9, 1, 0.9, 1) # Light green for active
                        else:
                            Color(1, 0.9, 0.9, 1) # Light red for inactive
                        card_box.rect = RoundedRectangle(pos=card_box.pos, size=card_box.size, radius=[12, 12, 12, 12])
                    card_box.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

                    r1 = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30))
                    lbl_name = Label(text=f"[b]{name}[/b]" + (" (ADMIN)" if is_admin else ""), markup=True, color=(0.1, 0.1, 0.2, 1), font_size='16sp', halign='left')
                    lbl_name.bind(size=lambda s, w: setattr(s, 'text_size', s.size))
                    
                    status_text = "ACTIVE" if is_active else "INACTIVE"
                    lbl_status = Label(text=status_text, bold=True, color=(0.1, 0.6, 0.2, 1) if is_active else (0.8, 0.2, 0.2, 1), font_size='13sp', size_hint_x=None, width=dp(90))
                    
                    r1.add_widget(lbl_name)
                    r1.add_widget(lbl_status)

                    r2 = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25))
                    lbl_mobile = Label(text=f"Mobile: {mobile}", color=(0.3, 0.3, 0.3, 1), font_size='14sp', halign='left')
                    lbl_mobile.bind(size=lambda s, w: setattr(s, 'text_size', s.size))
                    r2.add_widget(lbl_mobile)

                    r3 = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25))
                    lbl_email = Label(text=f"Email: {email}", color=(0.3, 0.3, 0.3, 1), font_size='13sp', halign='left')
                    lbl_email.bind(size=lambda s, w: setattr(s, 'text_size', s.size))
                    r3.add_widget(lbl_email)

                    card_box.add_widget(r1)
                    card_box.add_widget(r2)
                    card_box.add_widget(r3)

                    from kivy.uix.relativelayout import RelativeLayout
                    rel_layout = RelativeLayout(size_hint_y=None, height=dp(115))
                    card_box.size_hint = (1, 1)
                    rel_layout.add_widget(card_box)
                    
                    action_btn = Button(
                        text="",
                        background_normal='',
                        background_color=(0,0,0,0),
                        size_hint=(1, 1)
                    )
                    action_btn.bind(on_release=lambda x, k=user_key, info=u_info: self.open_user_action_popup(k, info))
                    rel_layout.add_widget(action_btn)

                    layout.add_widget(rel_layout)
        except Exception as e:
            print(f"Error loading users: {e}")

    def open_user_action_popup(self, user_key, user_info):
        name = user_info.get("name", "User")
        mobile = user_info.get("mobile", "")
        is_active = user_info.get("is_active", False)
        is_admin = user_info.get("is_admin", False) or (mobile == PRIMARY_ADMIN_MOBILE)

        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        lbl_info = Label(text=f"Manage User:\n[b]{name}[/b]\n({mobile})", markup=True, font_size='16sp', halign='center', valign='middle')
        lbl_info.bind(size=lambda s, w: setattr(s, 'text_size', s.size))

        btn_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(190))

        toggle_btn_text = "Make Inactive" if is_active else "Make Active"
        toggle_btn = Button(text=toggle_btn_text, bold=True, background_normal='', background_color=(0,0,0,0), color=(1,1,1,1))
        with toggle_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.85, 0.2, 0.2, 1) if is_active else Color(0.1, 0.7, 0.3, 1)
            toggle_btn.rect = RoundedRectangle(pos=toggle_btn.pos, size=toggle_btn.size, radius=[12, 12, 12, 12])
        toggle_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        admin_btn_text = "Remove Admin Rights" if is_admin else "Make Admin"
        admin_btn = Button(text=admin_btn_text, bold=True, background_normal='', background_color=(0,0,0,0), color=(1,1,1,1))
        with admin_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.8, 0.4, 0.1, 1) if is_admin else Color(0.1, 0.5, 0.8, 1)
            admin_btn.rect = RoundedRectangle(pos=admin_btn.pos, size=admin_btn.size, radius=[12, 12, 12, 12])
        admin_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        close_btn = Button(text="Close", bold=True, background_normal='', background_color=(0,0,0,0), color=(1,1,1,1))
        with close_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.5, 0.5, 0.5, 1)
            close_btn.rect = RoundedRectangle(pos=close_btn.pos, size=close_btn.size, radius=[12, 12, 12, 12])
        close_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        btn_layout.add_widget(toggle_btn)
        btn_layout.add_widget(admin_btn)
        btn_layout.add_widget(close_btn)

        popup = Popup(title="User Options", content=content, size_hint=(0.85, None), height=dp(340))
        content.add_widget(lbl_info)
        content.add_widget(btn_layout)

        def update_active_status(instance):
            try:
                new_status = not is_active
                requests.patch(f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/users/{user_key}.json", data=json.dumps({"is_active": new_status}))
                popup.dismiss()
                self.load_users()
            except Exception as e:
                print(e)

        def toggle_admin_status(instance):
            if mobile == PRIMARY_ADMIN_MOBILE:
                return 
            try:
                new_admin_status = not is_admin
                requests.patch(f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/users/{user_key}.json", data=json.dumps({"is_admin": new_admin_status}))
                popup.dismiss()
                self.load_users()
            except Exception as e:
                print(e)

        toggle_btn.bind(on_release=update_active_status)
        admin_btn.bind(on_release=toggle_admin_status)
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def go_back(self, instance=None):
        self.manager.current = 'home'


# --- INVENTORY SCREEN ---
class InventoryScreen(Screen):
    today_date = datetime.now().strftime("%d-%m-%Y")
    selected_image_paths = ListProperty([]) 
    
    def __init__(self, **kwargs):
        self.bank_list = ["HDFC Bank", "ICICI Bank", "Axis Bank", "SBI", "Kotak Bank"]
        self.repo_status_list = ["Pending", "Completed", "Hold", "Cancelled"]
        self.agent_list = []
        super(InventoryScreen, self).__init__(**kwargs)

    def on_enter(self):
        self.load_metadata_from_firebase()

    def load_metadata_from_firebase(self):
        app = App.get_running_app()
        current_mobile = str(getattr(app, 'logged_in_mobile', '')).strip()
        
        if not current_mobile:
            return

        try:
            response = requests.get(FIREBASE_META_URL)
            if response.status_code == 200 and response.json():
                meta_data = response.json()
                if isinstance(meta_data, dict) and current_mobile in meta_data:
                    user_meta = meta_data[current_mobile]
                    
                    if isinstance(user_meta, dict):
                        banks = user_meta.get("banks", [])
                        if isinstance(banks, list) and banks:
                            self.bank_list = list(set(self.bank_list + banks))
                            self.ids.bank_finance.values = self.bank_list
                            
                        statuses = user_meta.get("statuses", [])
                        if isinstance(statuses, list) and statuses:
                            self.repo_status_list = list(set(self.repo_status_list + statuses))
                            self.ids.repo_status.values = self.repo_status_list
                            
                        agents = user_meta.get("agents", [])
                        if isinstance(agents, list) and agents:
                            self.agent_list = agents
                            self.ids.repo_agent.values = self.agent_list
        except Exception as e:
            print(f"Error loading metadata: {e}")

    def open_gallery(self):
        try:
            from android.permissions import request_permissions, Permission
            permissions = [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            if hasattr(Permission, "READ_MEDIA_IMAGES"):
                permissions.append(Permission.READ_MEDIA_IMAGES)
            request_permissions(permissions)
        except Exception:
            pass

        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        possible_paths = ["/sdcard/DCIM", "/storage/emulated/0/DCIM", "/sdcard", "/storage/emulated/0", "/"]
        initial_path = "/"
        for p in possible_paths:
            if os.path.exists(p):
                initial_path = p
                break
        
        file_chooser = FileChooserIconView(
            path=initial_path,
            filters=['*.png', '*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.PNG'],
            multiselect=True
        )
        
        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        
        select_btn = Button(text="Select", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with select_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.1, 0.7, 0.3, 1)
            select_btn.rect = RoundedRectangle(pos=select_btn.pos, size=select_btn.size, radius=[15, 15, 15, 15])
        select_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        cancel_btn = Button(text="Cancel", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with cancel_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.8, 0.3, 0.3, 1)
            cancel_btn.rect = RoundedRectangle(pos=cancel_btn.pos, size=cancel_btn.size, radius=[15, 15, 15, 15])
        cancel_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
        
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(file_chooser)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Select Vehicle Images", content=content, size_hint=(0.9, 0.9))
        
        def on_select(instance):
            if file_chooser.selection:
                for path in file_chooser.selection:
                    if path not in self.selected_image_paths:
                        self.selected_image_paths.append(path)
                self.update_image_preview()
            popup.dismiss()
            
        select_btn.bind(on_release=on_select)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def remove_image(self, path_to_remove):
        if path_to_remove in self.selected_image_paths:
            self.selected_image_paths.remove(path_to_remove)
            self.update_image_preview()

    def show_full_image(self, image_path):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        full_img = Image(
            source=image_path,
            allow_stretch=True,
            keep_ratio=True
        )
        
        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        
        remove_btn = Button(
            text="Delete Image", 
            background_color=(0, 0, 0, 0), 
            background_normal='', 
            bold=True,
            color=(1, 1, 1, 1)
        )
        with remove_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.9, 0.2, 0.2, 1)
            remove_btn.rect = RoundedRectangle(pos=remove_btn.pos, size=remove_btn.size, radius=[15, 15, 15, 15])
        remove_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        close_btn = Button(
            text="Close", 
            background_color=(0, 0, 0, 0), 
            background_normal='', 
            bold=True,
            color=(1, 1, 1, 1)
        )
        with close_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.5, 0.5, 0.5, 1)
            close_btn.rect = RoundedRectangle(pos=close_btn.pos, size=close_btn.size, radius=[15, 15, 15, 15])
        close_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
        
        btn_layout.add_widget(remove_btn)
        btn_layout.add_widget(close_btn)
        
        content.add_widget(full_img)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Full Image View", content=content, size_hint=(0.9, 0.9))
        
        def on_remove(instance):
            self.remove_image(image_path)
            popup.dismiss()
            
        remove_btn.bind(on_release=on_remove)
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def update_image_preview(self):
        preview_grid = self.ids.image_preview_grid
        preview_grid.clear_widgets()
        
        for path in self.selected_image_paths:
            item_box = BoxLayout(
                orientation='vertical',
                size_hint=(None, None),
                size=(dp(90), dp(115)),
                spacing=dp(2)
            )
            
            img_btn = Button(
                background_normal=path,
                background_down=path,
                size_hint=(1, None),
                height=dp(85)
            )
            img_btn.bind(on_release=lambda btn, p=path: self.show_full_image(p))
            
            remove_btn = Button(
                text="Remove ✖",
                font_size='11sp',
                bold=True,
                size_hint_y=None,
                height=dp(25),
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=(1, 1, 1, 1)
            )
            with remove_btn.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(0.9, 0.2, 0.2, 1)
                remove_btn.rect = RoundedRectangle(pos=remove_btn.pos, size=remove_btn.size, radius=[8, 8, 8, 8])
            remove_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
            remove_btn.bind(on_release=lambda btn, p=path: self.remove_image(p))
            
            item_box.add_widget(img_btn)
            item_box.add_widget(remove_btn)
            preview_grid.add_widget(item_box)

    def show_add_bank_popup(self):
        self.show_dynamic_add_popup("Add New Bank", "bank")

    def show_add_status_popup(self):
        self.show_dynamic_add_popup("Add New Status", "status")

    def show_add_agent_popup(self):
        self.show_dynamic_add_popup("Add New Agent", "agent")

    def show_dynamic_add_popup(self, title_text, target_type):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        txt_input = TextInput(hint_text=f"Enter {target_type} name", multiline=False, size_hint_y=None, height=dp(45))
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))
        
        save_btn = Button(text="Save", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with save_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.1, 0.7, 0.3, 1)
            save_btn.rect = RoundedRectangle(pos=save_btn.pos, size=save_btn.size, radius=[15, 15, 15, 15])
        save_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        cancel_btn = Button(text="Cancel", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with cancel_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.6, 0.6, 0.6, 1)
            cancel_btn.rect = RoundedRectangle(pos=cancel_btn.pos, size=cancel_btn.size, radius=[15, 15, 15, 15])
        cancel_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(txt_input)
        content.add_widget(btn_layout)
        
        popup = Popup(title=title_text, content=content, size_hint=(0.85, None), height=dp(200))
        
        def save_item(instance):
            val = txt_input.text.strip()
            if val:
                app = App.get_running_app()
                current_mobile = str(getattr(app, 'logged_in_mobile', '')).strip()
                
                if target_type == "bank":
                    if val not in self.bank_list:
                        self.bank_list.append(val)
                        self.ids.bank_finance.values = self.bank_list
                    self.ids.bank_finance.text = val
                elif target_type == "status":
                    if val not in self.repo_status_list:
                        self.repo_status_list.append(val)
                        self.ids.repo_status.values = self.repo_status_list
                    self.ids.repo_status.text = val
                elif target_type == "agent":
                    if val not in self.agent_list:
                        self.agent_list.append(val)
                        self.ids.repo_agent.values = self.agent_list
                    self.ids.repo_agent.text = val
                
                if current_mobile:
                    try:
                        meta_payload = {
                            "banks": self.bank_list,
                            "statuses": self.repo_status_list,
                            "agents": self.agent_list
                        }
                        requests.patch(f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/metadata/{current_mobile}.json", data=json.dumps(meta_payload))
                    except Exception as e:
                        print(f"Error updating metadata to firebase: {e}")
            popup.dismiss()
            
        save_btn.bind(on_release=save_item)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def save_data(self):
        app = App.get_running_app()
        current_user = getattr(app, 'logged_in_user', '')
        current_mobile = str(getattr(app, 'logged_in_mobile', '')).strip()

        if not current_mobile:
            self.show_error_popup("Error: User mobile session missing! Kripya dobara login karein.")
            return

        date_val = self.ids.date_input.text.strip()
        vehicle_val = self.ids.vehicle_input.text.strip().upper()
        model_val = self.ids.model_input.text.strip()
        owner_val = self.ids.owner_input.text.strip()
        banker_val = self.ids.banker_input.text.strip()
        banker_mob = self.ids.mobile_input.text.strip()
        repo_charge_val = self.ids.repo_charge.text.strip()
        police_charge_val = self.ids.police_charge.text.strip()
        chain_charge_val = self.ids.chain_charge.text.strip()
        advance_val = self.ids.advance_input.text.strip()
        repo_status_val = self.ids.repo_status.text.strip()
        bank_finance_val = self.ids.bank_finance.text.strip()
        repo_agent_val = self.ids.repo_agent.text.strip()
        remark_val = self.ids.remark_input.text.strip()

        if not vehicle_val or not model_val or not owner_val or not banker_val:
            self.show_error_popup("Kripya sabhi zaroori fields (Vehicle, Model, Owner, Banker) bharein!")
            return

        if repo_status_val == 'Repo Status':
            repo_status_val = 'Pending'
        if bank_finance_val == 'Bank Finance':
            bank_finance_val = ''
        if repo_agent_val == 'Repo Agent':
            repo_agent_val = ''

        data_dict = {
            "date": date_val,
            "vehicle_no": vehicle_val,
            "model": model_val,
            "owner_name": owner_val,
            "banker_name": banker_val,
            "banker_mobile": banker_mob,
            "repo_charge": repo_charge_val,
            "police_charge": police_charge_val,
            "chain_charge": chain_charge_val,
            "advance": advance_val,
            "repo_status": repo_status_val,
            "bank_finance": bank_finance_val,
            "repo_agent": repo_agent_val,
            "remark": remark_val,
            "user_name": current_user,
            "user_mobile": current_mobile,
            "images": list(self.selected_image_paths)
        }

        try:
            response = requests.post(FIREBASE_URL, data=json.dumps(data_dict))
            if response.status_code == 200:
                self.show_success_popup()
                self.clear_form()
            else:
                self.show_error_popup("Database mein data save nahi ho saka. Dobara koshish karein.")
        except Exception as e:
            self.show_error_popup(f"Connection Error: {e}")

    def clear_form(self):
        self.ids.vehicle_input.text = ""
        self.ids.model_input.text = ""
        self.ids.owner_input.text = ""
        self.ids.banker_input.text = ""
        self.ids.mobile_input.text = ""
        self.ids.repo_charge.text = ""
        self.ids.police_charge.text = ""
        self.ids.chain_charge.text = ""
        self.ids.advance_input.text = ""
        self.ids.repo_status.text = 'Repo Status'
        self.ids.bank_finance.text = 'Bank Finance'
        self.ids.repo_agent.text = 'Repo Agent'
        self.ids.remark_input.text = ""
        self.selected_image_paths = []
        self.ids.image_preview_grid.clear_widgets()

    def show_error_popup(self, message):
        popup = Popup(title='Error', content=Label(text=message, halign='center', text_size=(dp(250), None)), size_hint=(0.8, None), height=dp(160))
        popup.open()

    def show_success_popup(self):
        popup = Popup(title='Success', content=Label(text='Inventory Successfully Saved!', halign='center'), size_hint=(0.7, None), height=dp(140))
        popup.open()


# --- LOGIN SCREEN ---
class LoginScreen(Screen):
    def limit_ten_digits(self, text_input, value):
        if len(value) > 10:
            text_input.text = value[:10]

    def limit_four_digits(self, text_input, value):
        if len(value) > 4:
            text_input.text = value[:4]

    def toggle_password_visibility(self, pwd_input, btn):
        pwd_input.password = not pwd_input.password
        btn.text = "👁 Hide" if not pwd_input.password else "👁 Show"

    def toggle_reg_password_visibility(self, pwd_input, btn):
        pwd_input.password = not pwd_input.password
        btn.text = "👁 Hide" if not pwd_input.password else "👁 Show"

    def toggle_new_password_visibility(self, pwd_input, btn):
        pwd_input.password = not pwd_input.password
        btn.text = "👁 Hide" if not pwd_input.password else "👁 Show"

    def verify_login(self, instance):
        u_mobile = self.ids.mobile_input.text.strip()
        u_pass = self.ids.password_input.text.strip()

        if not u_mobile:
            self.ids.error_label.text = "Please enter mobile number"
            return

        if len(u_mobile) != 10:
            self.ids.error_label.text = "Mobile number must be 10 digits"
            return

        if u_mobile == PRIMARY_ADMIN_MOBILE:
            app_instance = App.get_running_app()
            app_instance.logged_in_user = "Admin"
            app_instance.logged_in_email = "admin@mhbrother.com"
            app_instance.logged_in_mobile = u_mobile  
            
            self.ids.error_label.text = ""
            self.ids.mobile_input.text = ""
            self.ids.password_input.text = ""
            self.manager.current = 'home'
            return

        if not u_pass:
            self.ids.error_label.text = "Please enter 4-digit password"
            return

        try:
            response = requests.get(USERS_FIREBASE_URL)
            if response.status_code == 200:
                users_data = response.json() or {}

                login_success = False
                is_active_user = False
                user_name = ""
                user_email = ""
                
                for key, user_info in users_data.items():
                    if user_info.get("mobile") == u_mobile and user_info.get("password") == u_pass:
                        user_name = user_info.get("name", "User")
                        user_email = user_info.get("email", "")
                        is_active_user = user_info.get("is_active", False)
                        login_success = True
                        break
                
                if login_success:
                    if not is_active_user and not is_user_admin(u_mobile, users_data):
                        self.ids.error_label.text = "Account Inactive! Kripya Admin se active karwayein."
                        return

                    app_instance = App.get_running_app()
                    app_instance.logged_in_user = user_name
                    app_instance.logged_in_email = user_email
                    app_instance.logged_in_mobile = u_mobile  
                    
                    self.ids.error_label.text = ""
                    self.ids.mobile_input.text = ""
                    self.ids.password_input.text = ""
                    self.manager.current = 'home'
                else:
                    self.ids.error_label.text = "Invalid Mobile Number or Password"
            else:
                self.ids.error_label.text = "No users found in database!"
        except Exception as e:
            self.ids.error_label.text = "Connection Error!"
            print(f"Login Error: {e}")

    def show_register_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        
        self.reg_name = TextInput(hint_text='Full Name / Business Name', multiline=False, size_hint_y=None, height=dp(45))
        self.reg_mobile = TextInput(hint_text='Mobile Number (10 Digits)', multiline=False, input_filter='int', max_text_length=10, size_hint_y=None, height=dp(45))
        self.reg_mobile.bind(text=lambda inst, val: self.limit_ten_digits(inst, val))
        
        self.reg_email = TextInput(hint_text='Email Address', multiline=False, size_hint_y=None, height=dp(45))
        
        pwd_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45), spacing=dp(5))
        self.reg_password = TextInput(hint_text='4-Digit Password Only', password=True, multiline=False, input_filter='int', max_text_length=4, size_hint_y=1)
        self.reg_password.bind(text=lambda inst, val: self.limit_four_digits(inst, val))
        
        toggle_reg_btn = Button(text='👁 Show', font_size='12sp', size_hint=(None, 1), width=dp(70), background_normal='', background_color=(0.3, 0.3, 0.4, 1))
        toggle_reg_btn.bind(on_release=lambda x: self.toggle_reg_password_visibility(self.reg_password, toggle_reg_btn))
        pwd_box.add_widget(self.reg_password)
        pwd_box.add_widget(toggle_reg_btn)
        
        save_user_btn = Button(text='SAVE NEW USER', bold=True, size_hint_y=None, height=dp(45), background_normal='', background_color=(0, 0, 0, 0), color=(1, 1, 1, 1))
        with save_user_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.1, 0.7, 0.3, 1)
            save_user_btn.rect = RoundedRectangle(pos=save_user_btn.pos, size=save_user_btn.size, radius=[15, 15, 15, 15])
        save_user_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        self.reg_msg = Label(text='', color=(0.1, 0.7, 0.3, 1), font_size='13sp', size_hint_y=None, height=dp(25))
        
        content.add_widget(self.reg_name)
        content.add_widget(self.reg_mobile)
        content.add_widget(self.reg_email)
        content.add_widget(pwd_box)
        content.add_widget(save_user_btn)
        content.add_widget(self.reg_msg)
        
        self.reg_popup = Popup(title='Register New User', content=content, size_hint=(0.85, None), height=dp(355))
        save_user_btn.bind(on_release=self.save_new_user_to_firebase)
        self.reg_popup.open()

    def save_new_user_to_firebase(self, instance):
        name = self.reg_name.text.strip()
        mobile = self.reg_mobile.text.strip()
        email = self.reg_email.text.strip()
        password = self.reg_password.text.strip()

        if not name or not mobile or not password:
            self.reg_msg.color = (0.9, 0.2, 0.2, 1)
            self.reg_msg.text = "All required fields must be filled!"
            return

        if len(mobile) != 10 or not mobile.isdigit():
            self.reg_msg.color = (0.9, 0.2, 0.2, 1)
            self.reg_msg.text = "Mobile number must be exactly 10 digits!"
            return

        if len(password) != 4 or not password.isdigit():
            self.reg_msg.color = (0.9, 0.2, 0.2, 1)
            self.reg_msg.text = "Password must be exactly 4 digits!"
            return

        user_data = {
            "name": name, 
            "mobile": mobile, 
            "email": email, 
            "password": password,
            "is_active": False,
            "is_admin": False
        }

        try:
            response = requests.post(USERS_FIREBASE_URL, data=json.dumps(user_data))
            if response.status_code == 200:
                self.reg_msg.color = (0.1, 0.7, 0.3, 1)
                self.reg_msg.text = "Registered Successfully! (Account Inactive)"
                Clock.schedule_once(lambda dt: self.reg_popup.dismiss(), 1.5)
            else:
                self.reg_msg.color = (0.9, 0.2, 0.2, 1)
                self.reg_msg.text = "Failed to register. Try again!"
        except Exception as e:
            self.reg_msg.color = (0.9, 0.2, 0.2, 1)
            self.reg_msg.text = "Connection Error!"

    def show_forgot_password_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        self.forgot_name = TextInput(hint_text='Enter Full Name', multiline=False, size_hint_y=None, height=dp(45))
        self.forgot_mobile = TextInput(hint_text='Enter Mobile Number (10 Digits)', multiline=False, input_filter='int', max_text_length=10, size_hint_y=None, height=dp(45))
        self.forgot_mobile.bind(text=lambda inst, val: self.limit_ten_digits(inst, val))
        
        send_otp_btn = Button(text='GENERATE OTP', bold=True, size_hint_y=None, height=dp(45), background_normal='', background_color=(0, 0, 0, 0), color=(1, 1, 1, 1))
        with send_otp_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.9, 0.5, 0, 1)
            send_otp_btn.rect = RoundedRectangle(pos=send_otp_btn.pos, size=send_otp_btn.size, radius=[15, 15, 15, 15])
        send_otp_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        self.forgot_msg = Label(text='', color=(0.9, 0.2, 0.2, 1), font_size='13sp', size_hint_y=None, height=dp(25))

        content.add_widget(self.forgot_name)
        content.add_widget(self.forgot_mobile)
        content.add_widget(send_otp_btn)
        content.add_widget(self.forgot_msg)
        
        self.forgot_popup = Popup(title='Forgot Password', content=content, size_hint=(0.85, None), height=dp(270))
        send_otp_btn.bind(on_release=self.verify_user_and_generate_otp)
        self.forgot_popup.open()

    def verify_user_and_generate_otp(self, instance):
        u_name = self.forgot_name.text.strip()
        u_mobile = self.forgot_mobile.text.strip()

        if not u_name or not u_mobile:
            self.forgot_msg.text = "All fields are required!"
            return

        if len(u_mobile) != 10:
            self.forgot_msg.text = "Mobile number must be 10 digits!"
            return

        try:
            response = requests.get(USERS_FIREBASE_URL)
            if response.status_code == 200 and response.json():
                users_data = response.json()
                self.found_user_key = None
                
                for key, user_info in users_data.items():
                    if user_info.get("name") == u_name and user_info.get("mobile") == u_mobile:
                        self.found_user_key = key
                        break
                
                if self.found_user_key:
                    self.generated_otp = str(random.randint(1000, 9999))
                    self.forgot_popup.dismiss()
                    self.show_otp_display_popup(self.generated_otp)
                else:
                    self.forgot_msg.text = "Name or Mobile Number does not match!"
            else:
                self.forgot_msg.text = "Database error!"
        except Exception as e:
            self.forgot_msg.text = "Connection error!"

    def show_otp_display_popup(self, otp_code):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        info_label = Label(text=f"Your OTP Code is:\n[b]{otp_code}[/b]", markup=True, font_size='20sp', color=(0.1, 0.6, 0.3, 1), halign='center', valign='middle')
        info_label.bind(size=lambda s, w: setattr(s, 'text_size', s.size))
        
        next_btn = Button(text='ENTER THIS OTP', bold=True, size_hint_y=None, height=dp(45), background_normal='', background_color=(0, 0, 0, 0), color=(1, 1, 1, 1))
        with next_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.1, 0.5, 0.8, 1)
            next_btn.rect = RoundedRectangle(pos=next_btn.pos, size=next_btn.size, radius=[15, 15, 15, 15])
        next_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
        
        content.add_widget(info_label)
        content.add_widget(next_btn)
        
        self.display_popup = Popup(title='OTP Generated Successfully', content=content, size_hint=(0.85, None), height=dp(220))
        next_btn.bind(on_release=lambda x: (self.display_popup.dismiss(), self.show_otp_verification_popup()))
        self.display_popup.open()

    def show_otp_verification_popup(self):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        self.otp_input = TextInput(hint_text='Enter 4-Digit OTP', multiline=False, input_filter='int', max_text_length=4, size_hint_y=None, height=dp(45))
        self.otp_input.bind(text=lambda inst, val: self.limit_four_digits(inst, val))
        
        new_pwd_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45), spacing=dp(5))
        self.new_pass_input = TextInput(hint_text='New 4-Digit Password', password=True, multiline=False, input_filter='int', max_text_length=4, size_hint_y=1)
        self.new_pass_input.bind(text=lambda inst, val: self.limit_four_digits(inst, val))
        
        toggle_new_btn = Button(text='👁 Show', font_size='12sp', size_hint=(None, 1), width=dp(70), background_normal='', background_color=(0.3, 0.3, 0.4, 1))
        toggle_new_btn.bind(on_release=lambda x: self.toggle_new_password_visibility(self.new_pass_input, toggle_new_btn))
        new_pwd_box.add_widget(self.new_pass_input)
        new_pwd_box.add_widget(toggle_new_btn)
        
        verify_btn = Button(text='VERIFY & RESET PASSWORD', bold=True, size_hint_y=None, height=dp(45), background_normal='', background_color=(0, 0, 0, 0), color=(1, 1, 1, 1))
        with verify_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.1, 0.7, 0.3, 1)
            verify_btn.rect = RoundedRectangle(pos=verify_btn.pos, size=verify_btn.size, radius=[15, 15, 15, 15])
        verify_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        self.otp_msg = Label(text='', color=(0.9, 0.2, 0.2, 1), font_size='13sp', size_hint_y=None, height=dp(25))

        content.add_widget(self.otp_input)
        content.add_widget(new_pwd_box)
        content.add_widget(verify_btn)
        content.add_widget(self.otp_msg)
        
        self.otp_popup = Popup(title='Verify OTP & Reset', content=content, size_hint=(0.85, None), height=dp(270))
        verify_btn.bind(on_release=self.process_otp_and_reset)
        self.otp_popup.open()

    def process_otp_and_reset(self, instance):
        entered_otp = self.otp_input.text.strip()
        new_pass = self.new_pass_input.text.strip()

        if not entered_otp or not new_pass:
            self.otp_msg.text = "Please enter OTP and new password!"
            return

        if len(new_pass) != 4 or not new_pass.isdigit():
            self.otp_msg.text = "New password must be exactly 4 digits!"
            return

        if entered_otp == self.generated_otp:
            try:
                update_url = f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/users/{self.found_user_key}.json"
                requests.patch(update_url, data=json.dumps({"password": new_pass}))
                self.otp_msg.color = (0.1, 0.7, 0.3, 1)
                self.otp_msg.text = "Password updated successfully!"
                Clock.schedule_once(lambda dt: self.otp_popup.dismiss(), 1.5)
            except Exception as e:
                self.otp_msg.text = "Failed to update password!"
        else:
            self.otp_msg.text = "Invalid OTP! Please try again."


# --- VIEW SCREEN ---
class ViewScreen(Screen):
    search_query = ""
    search_type = ""
    current_searched_rows = []
    current_columns = []
    firebase_keys = []

    def on_enter(self):
        self.load_data()

    def load_data(self):
        layout = self.ids.data_layout
        layout.clear_widgets()
        layout.height = 0
        self.current_searched_rows = []
        self.firebase_keys = []

        app = App.get_running_app()
        current_mobile = str(getattr(app, 'logged_in_mobile', '')).strip()

        all_users = {}
        try:
            u_resp = requests.get(USERS_FIREBASE_URL)
            if u_resp.status_code == 200 and u_resp.json():
                all_users = u_resp.json()
        except Exception:
            pass

        user_is_admin = is_user_admin(current_mobile, all_users)

        firebase_rows = []
        fb_keys = []
        columns = [
            "date", "vehicle_no", "model", "owner_name", "banker_name", 
            "banker_mobile", "repo_charge", "police_charge", "chain_charge", 
            "advance", "repo_status", "bank_finance", "repo_agent", "remark", "images", "user_name"
        ]
        self.current_columns = columns

        try:
            response = requests.get(FIREBASE_URL)
            if response.status_code == 200 and response.json():
                data_json = response.json()
                for key, val in data_json.items():
                    if isinstance(val, dict):
                        val_mobile = str(val.get("user_mobile", "")).strip()
                        if user_is_admin or (current_mobile and val_mobile == current_mobile):
                            row = [
                                val.get("date", ""), val.get("vehicle_no", ""), val.get("model", ""),
                                val.get("owner_name", ""), val.get("banker_name", ""), val.get("banker_mobile", ""),
                                val.get("repo_charge", ""), val.get("police_charge", ""), val.get("chain_charge", ""),
                                val.get("advance", ""), val.get("repo_status", ""), val.get("bank_finance", ""),
                                val.get("repo_agent", ""), val.get("remark", ""), val.get("images", []), val.get("user_name", "")
                            ]
                            firebase_rows.append(row)
                            fb_keys.append(key)
        except Exception as e:
            print(f"Firebase Fetch Error: {e}")

        rows = firebase_rows
        self.firebase_keys = fb_keys

        if self.search_query and rows:
            filtered_rows = []
            filtered_keys = []
            q = self.search_query.lower()
            for r, k in zip(rows, fb_keys):
                if self.search_type == 'vehicle':
                    if q in str(r[1]).lower():
                        filtered_rows.append(r)
                        filtered_keys.append(k)
                elif self.search_type == 'agent':
                    agent_val = str(r[12]).lower() if len(r) > 12 else ""
                    if q in agent_val:
                        filtered_rows.append(r)
                        filtered_keys.append(k)
                elif self.search_type == 'user_name':
                    uname_val = str(r[15]).lower() if len(r) > 15 else ""
                    if q in uname_val:
                        filtered_rows.append(r)
                        filtered_keys.append(k)
                else:
                    filtered_rows.append(r)
                    filtered_keys.append(k)
            rows = filtered_rows
            self.firebase_keys = filtered_keys

        self.current_searched_rows = rows
        total_records = len(rows)

        if self.search_type == 'agent' and rows:
            db_agent_name = rows[0][12] if len(rows[0]) > 12 and rows[0][12] else self.search_query.title()
            self.ids.total_label.text = f"Repo Agent: {db_agent_name} ({len(rows)})"
        elif self.search_type == 'agent' and not rows:
            self.ids.total_label.text = f"Repo Agent: {self.search_query.title()} (0)"
        elif self.search_type == 'vehicle' and self.search_query:
            self.ids.total_label.text = f"Vehicle: {self.search_query.upper()} ({len(rows)})"
        elif self.search_type == 'user_name' and self.search_query:
            self.ids.total_label.text = f"User: {self.search_query.title()} ({len(rows)})"
        else:
            self.ids.total_label.text = f"{len(rows)} / {total_records} Showing"

        if self.search_type == 'agent' and len(rows) > 0:
            self.show_share_all_button()
        else:
            self.hide_share_all_button()

        vehicle_index = 1
        for i, col in enumerate(self.current_columns):
            if "vehicle" in col.lower():
                vehicle_index = i
                break

        for row, fb_key in zip(rows, self.firebase_keys):
            try:
                vehicle_no = str(row[vehicle_index])
                if not vehicle_no.strip():
                    vehicle_no = "No Number"
            except:
                vehicle_no = "NO DATA"

            btn_details = Button(
                text=f"  {vehicle_no}     ➔ VIEW", bold=True, font_size='15sp', halign='left',
                background_normal='', background_color=(0, 0, 0, 0), color=(0.1, 0.1, 0.1, 1), size_hint_x=0.82
            )
            btn_details.bind(size=lambda s, w: setattr(s, 'text_size', (s.width - 20, None)))
            btn_details.bind(on_release=lambda instance, r=row, c=self.current_columns: self.open_details(r, c))

            btn_delete = Button(
                text='DEL', bold=True, font_size='13sp', background_normal='',
                background_color=(0, 0, 0, 0), color=(1, 1, 1, 1), size_hint_x=0.18
            )
            with btn_delete.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(0.85, 0.2, 0.2, 1)
                btn_delete.rect = RoundedRectangle(pos=btn_delete.pos, size=btn_delete.size, radius=[8, 8, 8, 8])
            btn_delete.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
            
            btn_delete.bind(on_release=lambda instance, k=fb_key, r=row: self.delete_record(k, r))

            layout.add_widget(btn_details)
            layout.add_widget(btn_delete)

    def show_share_all_button(self):
        self.ids.share_all_container.height = dp(55)
        self.ids.share_all_container.opacity = 1

    def hide_share_all_button(self):
        self.ids.share_all_container.height = dp(0)
        self.ids.share_all_container.opacity = 0

    def share_all_agent_results(self):
        if not self.current_searched_rows:
            return

        msg_lines = [f"*MH BROTHER - Repo Agent Report: {self.search_query.title()}*"]
        msg_lines.append(f"Total Vehicles: {len(self.current_searched_rows)}\n")

        for idx, row in enumerate(self.current_searched_rows, 1):
            msg_lines.append(f"--- Record {idx} ---")
            for col, val in zip(self.current_columns, row):
                if col.lower() in ['id', 'images']:
                    continue
                col_name = str(col).replace("_", " ").title()
                msg_lines.append(f"{col_name}: {val if val else '-'}")
            msg_lines.append("")

        text_to_share = "\n".join(msg_lines)
        self.trigger_share_intent(text_to_share, "Share Agent Vehicles")

    def trigger_share_intent(self, text_to_share, chooser_title):
        try:
            from jnius import autoclass
            Intent = autoclass('android.content.Intent')
            String = autoclass('java.lang.String')
            
            intent = Intent()
            intent.setAction(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_TEXT, String(text_to_share))
            
            current_activity = autoclass('org.kivy.android.PythonActivity').mActivity
            current_activity.startActivity(Intent.createChooser(intent, String(chooser_title)))
        except Exception as e:
            content = BoxLayout(orientation='vertical', padding=10, spacing=10)
            txt_input = TextInput(text=text_to_share, readonly=True)
            close_btn = Button(text="Close", size_hint_y=None, height=40, background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
            with close_btn.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(0.2, 0.6, 0.8, 1)
                close_btn.rect = RoundedRectangle(pos=close_btn.pos, size=close_btn.size, radius=[15, 15, 15, 15])
            close_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

            content.add_widget(txt_input)
            content.add_widget(close_btn)
            
            popup = Popup(title=chooser_title, content=content, size_hint=(0.9, 0.7))
            close_btn.bind(on_release=popup.dismiss)
            popup.open()

    def delete_record(self, fb_key, row):
        vehicle_no = row[1] if len(row) > 1 else ""
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))
        lbl = Label(text=f"Delete record for vehicle\n{vehicle_no} from Firebase?", font_size='16sp', halign='center', valign='middle')
        lbl.bind(size=lambda s, w: setattr(s, 'text_size', s.size))
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))
        
        yes_btn = Button(text="Yes, Delete", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with yes_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.9, 0.2, 0.2, 1)
            yes_btn.rect = RoundedRectangle(pos=yes_btn.pos, size=yes_btn.size, radius=[15, 15, 15, 15])
        yes_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        no_btn = Button(text="Cancel", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with no_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.5, 0.5, 0.5, 1)
            no_btn.rect = RoundedRectangle(pos=no_btn.pos, size=no_btn.size, radius=[15, 15, 15, 15])
        no_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
        
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(lbl)
        content.add_widget(btn_layout)
        
        popup = Popup(title='Confirm Delete', content=content, size_hint=(0.85, None), height=dp(220))
        
        def confirm_del(instance):
            try:
                delete_url = f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/inventory/{fb_key}.json"
                requests.delete(delete_url)
            except Exception as e:
                print(f"Firebase Delete Error: {e}")
            popup.dismiss()
            self.load_data()
            
        yes_btn.bind(on_release=confirm_del)
        no_btn.bind(on_release=popup.dismiss)
        popup.open()

    def open_details(self, row, columns):
        details_screen = self.manager.get_screen('details')
        details_screen.load_details(row, columns)
        self.manager.current = 'details'

    def go_back(self):
        self.manager.current = 'home'


# --- HOME SCREEN & SIDEBAR ---
class SidebarMenu(ModalView):
    def __init__(self, **kwargs):
        super(SidebarMenu, self).__init__(**kwargs)
        self.auto_dismiss = False  
        app_instance = App.get_running_app()
        self.ids.sidebar_username_label.text = getattr(app_instance, 'logged_in_user', 'Guest')
        self.ids.sidebar_email_label.text = getattr(app_instance, 'logged_in_email', 'No Email')
        
        current_mobile = str(getattr(app_instance, 'logged_in_mobile', '')).strip()
        user_is_admin = False
        try:
            u_resp = requests.get(USERS_FIREBASE_URL)
            if u_resp.status_code == 200 and u_resp.json():
                user_is_admin = is_user_admin(current_mobile, u_resp.json())
        except Exception:
            user_is_admin = (current_mobile == PRIMARY_ADMIN_MOBILE)

        if not user_is_admin:
            self.ids.manage_user_btn.height = 0
            self.ids.manage_user_btn.opacity = 0
            self.ids.manage_user_btn.disabled = True
            
            self.ids.delete_account_btn.height = 0
            self.ids.delete_account_btn.opacity = 0
            self.ids.delete_account_btn.disabled = True
            
            self.ids.sidebar_bottom_layout.height = dp(75)

        self.touch_start_x = 0

    def on_touch_down(self, touch):
        self.touch_start_x = touch.x
        return super(SidebarMenu, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.touch_start_x - touch.x > dp(50):
            self.dismiss()
            return True
        return super(SidebarMenu, self).on_touch_up(touch)

    def navigate_to_manage_users(self):
        self.dismiss()
        app_instance = App.get_running_app()
        app_instance.root.current = 'manage_users'

    def confirm_delete_account(self):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))
        lbl = Label(text="Kya aap apna account aur sara data\ndatabase से permanently delete karna chahte hain?", font_size='15sp', halign='center', valign='middle')
        lbl.bind(size=lambda s, w: setattr(s, 'text_size', s.size))
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))
        
        yes_btn = Button(text="Yes, Delete", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with yes_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.9, 0.2, 0.2, 1)
            yes_btn.rect = RoundedRectangle(pos=yes_btn.pos, size=yes_btn.size, radius=[15, 15, 15, 15])
        yes_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))

        no_btn = Button(text="Cancel", background_color=(0, 0, 0, 0), background_normal='', bold=True, color=(1, 1, 1, 1))
        with no_btn.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.5, 0.5, 0.5, 1)
            no_btn.rect = RoundedRectangle(pos=no_btn.pos, size=no_btn.size, radius=[15, 15, 15, 15])
        no_btn.bind(pos=lambda s, p: setattr(s.rect, 'pos', p), size=lambda s, sz: setattr(s.rect, 'size', sz))
        
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(lbl)
        content.add_widget(btn_layout)
        
        popup = Popup(title='Confirm Account Deletion', content=content, size_hint=(0.85, None), height=dp(220))
        
        def execute_deletion(instance):
            app_instance = App.get_running_app()
            current_mobile = getattr(app_instance, 'logged_in_mobile', '')
            
            if current_mobile:
                try:
                    response = requests.get(USERS_FIREBASE_URL)
                    if response.status_code == 200 and response.json():
                        for key, user_info in response.json().items():
                            if user_info.get("mobile") == current_mobile:
                                requests.delete(f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/users/{key}.json")
                                break
                    
                    inv_response = requests.get(FIREBASE_URL)
                    if inv_response.status_code == 200 and inv_response.json():
                        for inv_key, inv_val in inv_response.json().items():
                            if isinstance(inv_val, dict) and str(inv_val.get("user_mobile", "")).strip() == str(current_mobile):
                                requests.delete(f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/inventory/{inv_key}.json")

                    meta_response = requests.get(FIREBASE_META_URL)
                    if meta_response.status_code == 200 and meta_response.json():
                        if current_mobile in meta_response.json():
                            requests.delete(f"https://mh-brother-app-default-rtdb.asia-southeast1.firebasedatabase.app/metadata/{current_mobile}.json")
                except Exception as e:
                    print(f"Error deleting account: {e}")
                
            popup.dismiss()
            app_instance.root.current = 'login'
            
        yes_btn.bind(on_release=execute_deletion)
        no_btn.bind(on_release=popup.dismiss)
        popup.open()


class HomeScreen(Screen):
    def on_enter(self):
        app = App.get_running_app()
        current_mobile = getattr(app, 'logged_in_mobile', '')
        
        user_is_admin = False
        try:
            u_resp = requests.get(USERS_FIREBASE_URL)
            if u_resp.status_code == 200 and u_resp.json():
                user_is_admin = is_user_admin(current_mobile, u_resp.json())
        except Exception:
            user_is_admin = (current_mobile == PRIMARY_ADMIN_MOBILE)

        if user_is_admin:
            self.ids.header_mobile_label.text = "MH BROTHER ADMIN"
            self.ids.home_agent_search.hint_text = "User Name"
        elif current_mobile:
            self.ids.header_mobile_label.text = "MH BROTHER"
            self.ids.home_agent_search.hint_text = "Agent Name"
        else:
            self.ids.header_mobile_label.text = "MH BROTHER"
            
        self.fetch_total_vehicles()

    def fetch_total_vehicles(self):
        try:
            app = App.get_running_app()
            current_mobile = str(getattr(app, 'logged_in_mobile', '')).strip()
            if not current_mobile:
                self.ids.total_vehicles_label.text = "0"
                return

            user_is_admin = False
            try:
                u_resp = requests.get(USERS_FIREBASE_URL)
                if u_resp.status_code == 200 and u_resp.json():
                    user_is_admin = is_user_admin(current_mobile, u_resp.json())
            except Exception:
                user_is_admin = (current_mobile == PRIMARY_ADMIN_MOBILE)

            response = requests.get(FIREBASE_URL)
            if response.status_code == 200 and response.json():
                data = response.json()
                if isinstance(data, dict):
                    if user_is_admin:
                        total_count = len(data)
                    else:
                        total_count = sum(1 for val in data.values() if isinstance(val, dict) and str(val.get("user_mobile", "")).strip() == current_mobile)
                    self.ids.total_vehicles_label.text = str(total_count)
                else:
                    self.ids.total_vehicles_label.text = "0"
            else:
                self.ids.total_vehicles_label.text = "0"
        except Exception as e:
            self.ids.total_vehicles_label.text = "0"

    def on_vehicle_text_change(self, text_input):
        text = text_input.text.strip()
        if len(text) >= 4:
            view_screen = self.manager.get_screen('view')
            view_screen.search_query = text
            view_screen.search_type = 'vehicle'
            Clock.schedule_once(lambda dt: setattr(text_input, 'text', ''), 0.1)
            self.manager.current = 'view'

    def on_agent_text_change(self, text_input):
        text = text_input.text.strip()
        if len(text) >= 3:
            app = App.get_running_app()
            current_mobile = str(getattr(app, 'logged_in_mobile', '')).strip()
            user_is_admin = False
            try:
                u_resp = requests.get(USERS_FIREBASE_URL)
                if u_resp.status_code == 200 and u_resp.json():
                    user_is_admin = is_user_admin(current_mobile, u_resp.json())
            except Exception:
                user_is_admin = (current_mobile == PRIMARY_ADMIN_MOBILE)

            view_screen = self.manager.get_screen('view')
            view_screen.search_query = text
            if user_is_admin:
                view_screen.search_type = 'user_name'  
            else:
                view_screen.search_type = 'agent'     
            
            Clock.schedule_once(lambda dt: setattr(text_input, 'text', ''), 0.1)
            self.manager.current = 'view'


# --- KV LAYOUT STRING ---
KV = '''
<SidebarMenu>:
    size_hint: (1, 1)
    background_color: 0, 0, 0, 0.5
    BoxLayout:
        orientation: 'horizontal'
        size_hint: (1, 1)
        BoxLayout:
            id: sidebar_content
            orientation: 'vertical'
            size_hint_x: 0.78
            size_hint_y: 1
            canvas.before:
                Color:
                    rgba: 0.95, 0.95, 0.98, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 25, 25, 0]
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(160)
                padding: dp(15), dp(12)
                spacing: dp(8)
                canvas.before:
                    Color:
                        rgba: 0.12, 0.16, 0.28, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [0, 25, 0, 0]
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(50)
                    spacing: dp(12)
                    Label:
                        text: 'MH'
                        bold: True
                        font_size: '16sp'
                        color: 0.12, 0.16, 0.28, 1
                        size_hint: None, None
                        size: dp(45), dp(45)
                        canvas.before:
                            Color:
                                rgba: 1, 0.8, 0.2, 1
                            Ellipse:
                                pos: self.pos
                                size: self.size
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: dp(2)
                        Label:
                            id: sidebar_username_label
                            text: 'Username'
                            bold: True
                            font_size: '18sp'
                            color: 1, 1, 1, 1
                            halign: 'left'
                            text_size: self.size
                            valign: 'middle'
                Label:
                    id: sidebar_email_label
                    text: 'email@example.com'
                    font_size: '13sp'
                    color: 0.8, 0.8, 0.8, 1
                    halign: 'left'
                    text_size: self.size
                    size_hint_y: None
                    height: dp(25)
            ScrollView:
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(12)
                    spacing: dp(8)
                    Button:
                        text: '    Dashboard  '
                        font_size: '15sp'
                        bold: True
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 0.15, 0.15, 0.2, 1
                        halign: 'left'
                        text_size: (self.width - dp(20), None)
                        valign: 'middle'
                        canvas.before:
                            Color:
                                rgba: 0.8, 0.85, 0.95, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: 
                            root.dismiss()
                            app.root.current = 'home'
                    Button:
                        text: '    View Confirmed'
                        font_size: '15sp'
                        bold: True
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 0.15, 0.15, 0.2, 1
                        halign: 'left'
                        text_size: (self.width - dp(20), None)
                        valign: 'middle'
                        canvas.before:
                            Color:
                                rgba: 0.8, 0.85, 0.95, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: 
                            root.dismiss()
                            view_screen = app.root.get_screen('view')
                            view_screen.search_query = ""
                            view_screen.search_type = ""
                            app.root.current = 'view'
                    Button:
                        text: '    Inventory Entry'
                        font_size: '15sp'
                        bold: True
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 0.15, 0.15, 0.2, 1
                        halign: 'left'
                        text_size: (self.width - dp(20), None)
                        valign: 'middle'
                        canvas.before:
                            Color:
                                rgba: 0.8, 0.85, 0.95, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: 
                            root.dismiss()
                            app.root.current = 'inventory'
                    Button:
                        id: manage_user_btn
                        text: '    Manage User Status'
                        font_size: '15sp'
                        bold: True
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 0.15, 0.15, 0.2, 1
                        halign: 'left'
                        text_size: (self.width - dp(20), None)
                        valign: 'middle'
                        canvas.before:
                            Color:
                                rgba: 0.8, 0.85, 0.95, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: 
                            root.dismiss()
                            root.navigate_to_manage_users()
                    Button:
                        text: '    Sync Offline'
                        font_size: '15sp'
                        bold: True
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 0.15, 0.15, 0.2, 1
                        halign: 'left'
                        text_size: (self.width - dp(20), None)
                        valign: 'middle'
                        canvas.before:
                            Color:
                                rgba: 0.8, 0.85, 0.95, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: root.dismiss()
            BoxLayout:
                id: sidebar_bottom_layout
                orientation: 'vertical'
                size_hint_y: None
                height: dp(130)
                padding: dp(15)
                spacing: dp(10)
                Button:
                    id: delete_account_btn
                    text: 'Delete Account'
                    bold: True
                    font_size: '14sp'
                    size_hint_y: None
                    height: dp(45)
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    color: 1, 1, 1, 1
                    canvas.before:
                        Color:
                            rgba: 0.85, 0.2, 0.2, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [15, 15, 15, 15]
                    on_release: 
                        root.dismiss()
                        root.confirm_delete_account()
                Button:
                    text: 'Sign Out'
                    bold: True
                    font_size: '15sp'
                    size_hint_y: None
                    height: dp(45)
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    color: 1, 1, 1, 1
                    canvas.before:
                        Color:
                            rgba: 0.25, 0.25, 0.3, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [15, 15, 15, 15]
                    on_release: 
                        root.dismiss()
                        app.root.current = 'login'
        Widget:
            size_hint_x: 0.22

<ManageUsersScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.94, 0.95, 0.98, 1
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(75)
            padding: dp(12)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 0.12, 0.16, 0.28, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 0, 25, 25]
            Button:
                text: 'BACK'
                size_hint_x: None
                width: dp(60)
                font_size: '12sp'
                bold: True
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 0.8, 0.2, 0.2, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: root.go_back()
            Label:
                text: 'Manage Users'
                bold: True
                color: 1, 1, 1, 1
                font_size: '20sp'
            Widget:
                size_hint_x: None
                width: dp(60)
        BoxLayout:
            size_hint_y: None
            height: dp(45)
            padding: dp(15), 0
            Label:
                id: users_count_label
                text: 'Loading users...'
                color: 0.2, 0.2, 0.3, 1
                bold: True
                font_size: '15sp'
                halign: 'left'
                valign: 'middle'
                text_size: self.size
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: users_layout
                orientation: 'vertical'
                padding: dp(15)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height

<LoginScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: 0.12, 0.16, 0.28, 1
            Rectangle:
                pos: self.pos
                size: self.size
        AnchorLayout:
            anchor_x: 'center'
            anchor_y: 'center'
            size_hint_y: None
            height: dp(90)
            Label:
                text: 'MH'
                bold: True
                font_size: '28sp'
                color: 0.12, 0.16, 0.28, 1
                size_hint: None, None
                size: dp(80), dp(80)
                canvas.before:
                    Color:
                        rgba: 1, 0.8, 0.2, 1
                    Ellipse:
                        pos: self.pos
                        size: self.size
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(55)
            spacing: dp(2)
            Label:
                text: 'MH BROTHER'
                bold: True
                font_size: '20sp'
                color: 1, 1, 1, 1
                halign: 'center'
                valign: 'middle'
                text_size: self.size
            Label:
                text: '9664118527'
                font_size: '14sp'
                color: 0.7, 0.85, 1, 1
                halign: 'center'
                valign: 'middle'
                text_size: self.size
        TextInput:
            id: mobile_input
            hint_text: 'Mobile Number (10 Digits)'
            multiline: False
            input_filter: 'int'
            max_text_length: 10
            size_hint_y: None
            height: dp(50)
            background_active: ''
            background_normal: ''
            padding: [dp(15), dp(12), dp(15), dp(12)]
            on_text: root.limit_ten_digits(self, self.text)
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(50)
            spacing: dp(5)
            TextInput:
                id: password_input
                hint_text: '4-Digit Password (Admin empty)'
                password: True
                multiline: False
                input_filter: 'int'
                max_text_length: 4
                size_hint_y: 1
                background_active: ''
                background_normal: ''
                padding: [dp(15), dp(12), dp(15), dp(12)]
                on_text: root.limit_four_digits(self, self.text)
            Button:
                text: '👁 Show'
                font_size: '12sp'
                size_hint: (None, 1)
                width: dp(80)
                background_normal: ''
                background_color: 0.3, 0.3, 0.4, 1
                color: 1, 1, 1, 1
                on_release: root.toggle_password_visibility(password_input, self)
        Button:
            text: 'LOGIN'
            bold: True
            font_size: '16sp'
            size_hint_y: None
            height: dp(48)
            background_normal: ''
            background_color: 0, 0, 0, 0
            color: 1, 1, 1, 1
            canvas.before:
                Color:
                    rgba: 0, 0.7, 0.4, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [20, 20, 20, 20]
            on_release: root.verify_login(self)
        Button:
            text: 'Forgot Password?'
            bold: True
            font_size: '13sp'
            size_hint_y: None
            height: dp(30)
            background_normal: ''
            background_color: 0, 0, 0, 0
            color: 0.4, 0.8, 1, 1
            on_release: root.show_forgot_password_popup(self)
        Button:
            text: 'Add New User (Register)'
            bold: True
            font_size: '14sp'
            size_hint_y: None
            height: dp(42)
            background_normal: ''
            background_color: 0, 0, 0, 0
            color: 1, 1, 1, 1
            canvas.before:
                Color:
                    rgba: 0.1, 0.5, 0.8, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [20, 20, 20, 20]
            on_release: root.show_register_popup(self)
        Label:
            id: error_label
            text: ''
            color: 1, 0.4, 0.4, 1
            font_size: '14sp'
            size_hint_y: None
            height: dp(25)

<HomeScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.94, 0.95, 0.98, 1
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(75)
            padding: dp(10)
            spacing: dp(8)
            canvas.before:
                Color:
                    rgba: 0.12, 0.16, 0.28, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 0, 25, 25]
            TextInput:
                id: home_vehicle_search
                hint_text: 'Vehicle No'
                multiline: False
                font_size: '12sp'
                size_hint_y: None
                height: dp(45)
                on_text: root.on_vehicle_text_change(self)
            TextInput:
                id: home_agent_search
                hint_text: 'Agent / User Name'
                multiline: False
                font_size: '12sp'
                size_hint_y: None
                height: dp(45)
                on_text: root.on_agent_text_change(self)
            Button:
                text: 'MENU'
                font_size: '12sp'
                bold: True
                size_hint: None, None
                size: dp(65), dp(45)
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 1, 0.6, 0.1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: app.open_global_menu(self)
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(15)
                spacing: dp(15)
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(160)
                    spacing: dp(5)
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [20, 20, 20, 20]
                    AnchorLayout:
                        anchor_x: 'center'
                        anchor_y: 'center'
                        size_hint_y: None
                        height: dp(65)
                        Label:
                            text: 'MH'
                            bold: True
                            font_size: '22sp'
                            color: 1, 1, 1, 1
                            size_hint: None, None
                            size: dp(60), dp(60)
                            canvas.before:
                                Color:
                                    rgba: 0.12, 0.16, 0.28, 1
                                Ellipse:
                                    pos: self.pos
                                    size: self.size
                    Label:
                        text: 'MH BROTHER'
                        bold: True
                        color: 0.12, 0.16, 0.28, 1
                        font_size: '17sp'
                        size_hint_y: None
                        height: dp(22)
                        halign: 'center'
                    Label:
                        text: '9664118527'
                        bold: True
                        color: 0.1, 0.5, 0.8, 1
                        font_size: '13sp'
                        size_hint_y: None
                        height: dp(18)
                        halign: 'center'
                    Label:
                        id: header_mobile_label
                        text: 'MH BROTHER'
                        color: 0.5, 0.5, 0.6, 1
                        font_size: '12sp'
                        size_hint_y: None
                        height: dp(18)
                        halign: 'center'
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(85)
                    spacing: dp(12)
                    BoxLayout:
                        orientation: 'vertical'
                        padding: dp(12)
                        spacing: dp(5)
                        canvas.before:
                            Color:
                                rgba: 0.85, 0.92, 1, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        Label:
                            text: 'Remaining Days'
                            color: 0.2, 0.3, 0.5, 1
                            font_size: '13sp'
                            bold: True
                        Label:
                            text: '0'
                            color: 0.1, 0.2, 0.4, 1
                            font_size: '20sp'
                            bold: True
                    BoxLayout:
                        orientation: 'vertical'
                        padding: dp(12)
                        spacing: dp(5)
                        canvas.before:
                            Color:
                                rgba: 0.9, 1, 0.9, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        Label:
                            text: 'Total Vehicles'
                            color: 0.2, 0.5, 0.2, 1
                            font_size: '13sp'
                            bold: True
                        Label:
                            id: total_vehicles_label
                            text: '0'
                            color: 0.1, 0.4, 0.1, 1
                            font_size: '20sp'
                            bold: True
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(75)
                    spacing: dp(12)
                    Button:
                        text: 'My Account'
                        bold: True
                        font_size: '15sp'
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 0.3, 0.3, 0.3, 1
                        disabled: True
                        canvas.before:
                            Color:
                                rgba: 0.9, 0.9, 0.9, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                    Button:
                        text: 'V. Confirmed'
                        bold: True
                        font_size: '15sp'
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 0.3, 0.3, 0.3, 1
                        disabled: True
                        canvas.before:
                            Color:
                                rgba: 0.9, 0.9, 0.9, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                Button:
                    text: 'Control Panel'
                    bold: True
                    font_size: '16sp'
                    size_hint_y: None
                    height: dp(60)
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    color: 0.3, 0.3, 0.3, 1
                    disabled: True
                    canvas.before:
                        Color:
                            rgba: 0.9, 0.9, 0.9, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [15, 15, 15, 15]
                Widget:
                    size_hint_y: None
                    height: dp(20)

<InventoryScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.94, 0.95, 0.98, 1
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(75)
            padding: dp(12)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 0.12, 0.16, 0.28, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 0, 25, 25]
            BoxLayout:
                size_hint_x: None
                width: dp(45)
                AnchorLayout:
                    anchor_x: 'center'
                    anchor_y: 'center'
                    Label:
                        text: 'MH'
                        bold: True
                        font_size: '12sp'
                        color: 0.12, 0.16, 0.28, 1
                        size_hint: None, None
                        size: dp(35), dp(35)
                        canvas.before:
                            Color:
                                rgba: 1, 0.8, 0.2, 1
                            Ellipse:
                                pos: self.pos
                                size: self.size
            Label:
                text: 'MH BROTHER'
                bold: True
                color: 1, 1, 1, 1
                font_size: '20sp'
            Button:
                text: 'MENU'
                font_size: '12sp'
                bold: True
                size_hint: None, None
                size: dp(60), dp(45)
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 1, 0.6, 0.1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: app.open_global_menu(self)
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(15)
                padding: dp(20)
                canvas.before:
                    Color:
                        rgba: 1, 1, 1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [20, 20, 20, 20]
                TextInput:
                    id: date_input
                    text: root.today_date
                    readonly: True
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: vehicle_input
                    hint_text: 'Vehicle No (Required)'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: model_input
                    hint_text: 'Model (Required)'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: owner_input
                    hint_text: 'Owner Name (Required)'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: banker_input
                    hint_text: 'Banker Name (Required)'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: mobile_input
                    hint_text: 'Banker Mobile (10 Digits Required)'
                    multiline: False
                    input_filter: 'int'
                    max_text_length: 10
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: repo_charge
                    hint_text: 'Repo Charge'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: police_charge
                    hint_text: 'Police Charge'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: chain_charge
                    hint_text: 'Chain Charge'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                TextInput:
                    id: advance_input
                    hint_text: 'Advance'
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(50)
                    spacing: dp(10)
                    Spinner:
                        id: repo_status
                        text: 'Repo Status'
                        values: root.repo_status_list
                        size_hint_x: 0.82
                    Button:
                        text: '+'
                        size_hint_x: 0.18
                        bold: True
                        font_size: '22sp'
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 1, 1, 1, 1
                        canvas.before:
                            Color:
                                rgba: 0.1, 0.5, 0.8, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: root.show_add_status_popup()
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(50)
                    spacing: dp(10)
                    Spinner:
                        id: bank_finance
                        text: 'Bank Finance'
                        values: root.bank_list
                        size_hint_x: 0.82
                    Button:
                        text: '+'
                        size_hint_x: 0.18
                        bold: True
                        font_size: '22sp'
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 1, 1, 1, 1
                        canvas.before:
                            Color:
                                rgba: 0.1, 0.5, 0.8, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: root.show_add_bank_popup()
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(50)
                    spacing: dp(10)
                    Spinner:
                        id: repo_agent
                        text: 'Repo Agent'
                        values: root.agent_list
                        size_hint_x: 0.82
                    Button:
                        text: '+'
                        size_hint_x: 0.18
                        bold: True
                        font_size: '22sp'
                        background_normal: ''
                        background_color: 0, 0, 0, 0
                        color: 1, 1, 1, 1
                        canvas.before:
                            Color:
                                rgba: 0.1, 0.5, 0.8, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [15, 15, 15, 15]
                        on_release: root.show_add_agent_popup()
                TextInput:
                    id: remark_input
                    hint_text: 'Remark'
                    multiline: True
                    size_hint_y: None
                    height: dp(130)
                Button:
                    text: 'SELECT IMAGES FROM GALLERY'
                    size_hint_y: None
                    height: dp(50)
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    color: 1, 1, 1, 1
                    bold: True
                    font_size: '14sp'
                    canvas.before:
                        Color:
                            rgba: 0.2, 0.6, 0.9, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [15, 15, 15, 15]
                    on_release: root.open_gallery()
                ScrollView:
                    size_hint_y: None
                    height: dp(125) if len(root.selected_image_paths) > 0 else dp(0)
                    opacity: 1 if len(root.selected_image_paths) > 0 else 0
                    do_scroll_x: True
                    do_scroll_y: False
                    GridLayout:
                        id: image_preview_grid
                        rows: 1
                        spacing: dp(10)
                        size_hint_x: None
                        width: self.minimum_width
                        padding: dp(5)
                Button:
                    text: 'SAVE INVENTORY'
                    size_hint_y: None
                    height: dp(60)
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    color: 1, 1, 1, 1
                    bold: True
                    font_size: '18sp'
                    canvas.before:
                        Color:
                            rgba: 0, 0.7, 0.35, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [20, 20, 20, 20]
                    on_release: root.save_data()
                Widget:
                    size_hint_y: None
                    height: dp(40)

<ViewScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.94, 0.95, 0.98, 1
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(75)
            padding: dp(12)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 0.12, 0.16, 0.28, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 0, 25, 25]
            Button:
                text: 'BACK'
                size_hint_x: None
                width: dp(60)
                font_size: '12sp'
                bold: True
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 0.8, 0.2, 0.2, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: root.go_back()
            Label:
                text: 'MH BROTHER'
                bold: True
                color: 1, 1, 1, 1
                font_size: '22sp'
            Button:
                text: 'MENU'
                font_size: '12sp'
                bold: True
                size_hint: None, None
                size: dp(60), dp(45)
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 1, 0.6, 0.1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: app.open_global_menu(self)
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            padding: dp(15), 0
            Label:
                id: total_label
                text: '0 / 0 Showing'
                color: 0.15, 0.15, 0.2, 1
                bold: True
                font_size: '17sp'
                halign: 'left'
                valign: 'middle'
                text_size: self.size
            Button:
                text: 'Online'
                size_hint: None, None
                size: dp(85), dp(35)
                font_size: '15sp'
                bold: True
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 0.1, 0.1, 0.1, 1
                canvas.before:
                    Color:
                        rgba: 1, 0.75, 0.1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [12, 12, 12, 12]
        BoxLayout:
            id: share_all_container
            size_hint_y: None
            height: dp(0)
            padding: dp(12), dp(0)
            opacity: 0
            Button:
                id: share_all_btn
                text: 'Share All Search Results'
                bold: True
                font_size: '15sp'
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                size_hint_y: None
                height: dp(45)
                canvas.before:
                    Color:
                        rgba: 0.1, 0.6, 0.9, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: root.share_all_agent_results()
        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: data_layout
                cols: 2
                spacing: dp(4)
                padding: dp(10)
                size_hint_y: None
                height: self.minimum_height
                row_default_height: dp(60)
                row_force_default: True

<DetailsScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.94, 0.95, 0.98, 1
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(75)
            padding: dp(12)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 0.12, 0.16, 0.28, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 0, 25, 25]
            Button:
                text: 'BACK'
                size_hint_x: None
                width: dp(60)
                font_size: '12sp'
                bold: True
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 0.8, 0.2, 0.2, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: root.go_back()
            Label:
                text: 'Vehicle Details'
                bold: True
                color: 1, 1, 1, 1
                font_size: '22sp'
            Button:
                text: 'MENU'
                font_size: '12sp'
                bold: True
                size_hint: None, None
                size: dp(60), dp(45)
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 1, 0.6, 0.1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]
                on_release: app.open_global_menu(self)
        AnchorLayout:
            anchor_x: 'right'
            size_hint_y: None
            height: dp(45)
            padding: dp(12), 0
            Button:
                text: 'Online'
                size_hint: None, None
                size: dp(90), dp(35)
                font_size: '15sp'
                bold: True
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: 0.1, 0.1, 0.1, 1
                canvas.before:
                    Color:
                        rgba: 1, 0.75, 0.1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [12, 12, 12, 12]
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: details_layout
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(10)
                size_hint_y: None
                height: self.minimum_height
'''

Builder.load_string(KV)


# --- MAIN APP CLASS ---
class MHBrotherDashboard(App):
    logged_in_user = ""
    logged_in_email = ""
    logged_in_mobile = ""

    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(InventoryScreen(name='inventory'))
        sm.add_widget(ViewScreen(name='view'))
        sm.add_widget(DetailsScreen(name='details'))
        sm.add_widget(ManageUsersScreen(name='manage_users'))
        return sm

    def open_global_menu(self, instance):
        sidebar = SidebarMenu()
        sidebar.open()


if __name__ == '__main__':
    MHBrotherDashboard().run()

from main_file import decrypt_ds2_sl2, encrypt_modified_files
import json
import os
import glob
import struct
from pathlib import Path




#path
userdata_path=None
import_path=None

#bytes
data=None
imported_data=None

#other
MODE=None
ga_weapons=[]
ga_armors=[]
ga_relic=[]
ga_empty=[]
ga_items=[]
char_name_list=[]


working_directory = os.path.dirname(os.path.abspath(__file__))
working_directory = Path(working_directory)  # convert to Path
os.chdir(working_directory)


items_json = {}
effects_json = {} 

def load_json_data():
    global items_json, effects_json, ill_effects_json
    try:
        file_path = os.path.join(working_directory, "Resources/Json")
        with open(os.path.join(file_path, 'items.json'), 'r') as f:
            items_json = json.load(f)
        with open(os.path.join(file_path, 'effects.json'), 'r') as f:
            effects_json = json.load(f)
        with open(os.path.join(file_path, 'illegal_effects.json'), 'r') as f:
            ill_effects_json = json.load(f)
    except FileNotFoundError:
        print("JSON files not found. Manual editing only will be available.")
        items_json = {}
        effects_json = {}
        ill_effects_json = {}

#helpers
def find_hex_offset(section_data, hex_pattern):
    try:
        pattern_bytes = bytes.fromhex(hex_pattern)
        if pattern_bytes in section_data:
            return section_data.index(pattern_bytes)
        return None
    except ValueError as e:
        return None
    
def find_value_at_offset(section_data, offset, byte_size=4):
    try:
        value_bytes = section_data[offset:offset+byte_size]
        if len(value_bytes) == byte_size:
            return int.from_bytes(value_bytes, 'little')
    except IndexError:
        pass
    return None

def write_value_at_offset(data, offset, value, byte_size=4):
    value_bytes = value.to_bytes(byte_size, 'little')
    # Replace the bytes at the given offset with the new value
    return data[:offset] + value_bytes + data[offset+byte_size:]

############
def split_files(file_path, folder_name):
    file_name = os.path.basename(file_path)

    # Case 1: If file name is memory.dat
    if file_name.lower() == 'memory.dat':
        split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder_name)
        os.makedirs(split_dir, exist_ok=True)

        with open(file_path, "rb") as f:
            # 1. Header (0x70 bytes)
            header = f.read(0x70)
            with open(os.path.join(split_dir, "header"), "wb") as out:
                out.write(header)

            # 2. userdata0 - userdata9 (each 0x27FFFF bytes)
            chunk_size = 0x280000
            for i in range(10):
                data = f.read(chunk_size)
                if not data:  # stop if file ends early
                    break
                with open(os.path.join(split_dir, f"userdata{i}"), "wb") as out:
                    out.write(data)

            # 3. Regulation (remaining bytes)
            regulation = f.read()
            if regulation:
                with open(os.path.join(split_dir, "regulation"), "wb") as out:
                    out.write(regulation)


    if file_name== 'NR0000.sl2': ##FIX
        split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder_name)
        os.makedirs(split_dir, exist_ok=True)
        unpacked_folder = decrypt_ds2_sl2(file_path)
        userdata_files = sorted(glob.glob(os.path.join(unpacked_folder, "USERDATA_*")))

def open_file():
    global MODE

    file_path= input("Enter the path to your save file (NR0000.sl2):    ")
    #file_path=filedialog.askopenfilename()
    if not file_path:
        return
    
    file_name = os.path.basename(file_path)

    split_files(file_path, 'decrypted_output')

    if file_name.lower() == 'memory.dat':
        MODE='PS4'
        name_to_path()

    elif file_name== 'NR0000.sl2':
        MODE='PC'
        name_to_path()

def load_file():

    open_file()
    for name, path in char_name_list:
        print('char name: ', name)
    name=input("Enter a char name to continue: ")
    for char, path in char_name_list:
        if char== name:
            global userdata_path
            userdata_path= path
            print(f"Loaded {char} from {path}")
            break
    with open(userdata_path, "rb") as f:
        global data
        data = f.read()
    gaprint(data)
    print(ga_relic)

    

ITEM_TYPE_EMPTY = 0x00000000
ITEM_TYPE_WEAPON = 0x80000000
ITEM_TYPE_ARMOR  = 0x90000000
ITEM_TYPE_RELIC  = 0xC0000000    

class Item:

    BASE_SIZE= 8

    def __init__(
            self,
            gaitem_handle,
            item_id,
            effect_1,
            effect_2,
            effect_3,
            durability,
            unk_1,
            sec_effect1,
            sec_effect2,
            sec_effect3,
            unk_2,
            offset,
            extra=None,
            size=BASE_SIZE,
        ):

            self.gaitem_handle = gaitem_handle
            self.item_id = item_id

            self.effect_1 = effect_1
            self.effect_2 = effect_2
            self.effect_3 = effect_3

            self.durability = durability
            self.unk_1 = unk_1

            self.sec_effect1 = sec_effect1
            self.sec_effect2 = sec_effect2
            self.sec_effect3 = sec_effect3
            self.unk_2 = unk_2

            self.offset = offset
            self.size = size

            # padding / extra bytes
            self.padding = extra or ()

    @classmethod
    def from_bytes(cls, data_type, offset=0):
        gaitem_handle, item_id = struct.unpack_from("<II", data_type, offset)
        type_bits = gaitem_handle & 0xF0000000
        cursor = offset + cls.BASE_SIZE
        size = cls.BASE_SIZE

        durability = unk_1 = unk_2 =0
        effect_1 = effect_2 = effect_3 = 0
        sec_effect1 = sec_effect2 = sec_effect3 = 0
        padding = ()

        if gaitem_handle != 0:
            if type_bits == ITEM_TYPE_WEAPON:
                cursor += 72  # skip weapon
                size = cursor - offset
            elif type_bits == ITEM_TYPE_ARMOR:
                cursor += 8   # skip armor
                size = cursor - offset
            elif type_bits == ITEM_TYPE_RELIC: #72 bytes
                # Parse relic
                durability, unk_1 = struct.unpack_from("<II", data_type, cursor)
                cursor += 8
                effect_1, effect_2, effect_3 = struct.unpack_from("<II I", data_type, cursor)
                cursor += 12
                padding = struct.unpack_from("<7I", data_type, cursor)  # 28 bytes
                cursor += 0x1C
                sec_effect1, sec_effect2, sec_effect3 = struct.unpack_from("<II I", data_type, cursor)
                cursor += 12
                unk_2= struct.unpack_from("<I", data_type, cursor)[0]
                cursor += 4
                size = cursor - offset

        return cls(
            gaitem_handle,
            item_id,
            effect_1,
            effect_2,
            effect_3,
            durability,
            unk_1,
            sec_effect1,
            sec_effect2,
            sec_effect3,
            unk_2,
            offset,
            extra=padding,
            size=size
        )

    


def parse_items(data_type, start_offset, slot_count=5120):
    items = []
    offset = start_offset

    for _ in range(slot_count):
        item = Item.from_bytes(data_type, offset)
        items.append(item)
        
        offset += item.size  

    return items, offset

def gaprint(data_type):
    global ga_weapons, ga_armors, ga_relic, ga_empty, ga_items

    save_data = data_type
    ga_items = []
    ga_weapons = []
    ga_armors = []
    ga_relic = []
    ga_empty = []

    start_offset = 0x14
    slot_count = 5120  # number of item slots

    items, end_offset = parse_items(save_data, start_offset, slot_count)

    # categorize items
    for item in items:
        type_bits = item.gaitem_handle & 0xF0000000
        ga_items.append(
        (
            item.gaitem_handle,
            item.item_id,
            item.effect_1,
            item.effect_2,
            item.effect_3,
            item.sec_effect1,
            item.sec_effect2,
            item.sec_effect3,
            item.offset,
            item.size
        )
    )
        if type_bits == ITEM_TYPE_RELIC:
            ga_relic.append(
        (
            item.gaitem_handle,
            item.item_id,
            item.effect_1,
            item.effect_2,
            item.effect_3,
            item.sec_effect1,
            item.sec_effect2,
            item.sec_effect3,
            item.offset,
            item.size
        )
    )

    return end_offset


def read_char_name(data):

    name_offset= gaprint(data)

    name_offset+=0x94

    max_chars = 16
    raw_name = data[name_offset:name_offset + max_chars * 2]
    name = raw_name.decode("utf-16-le", errors="ignore").rstrip("\x00")
    if name == "":
        return None

    return name

def name_to_path():
    global char_name_list

    unpacked_folder = working_directory / 'decrypted_output'
    if MODE== 'PS4':
        for i in range(10):

            file_path = os.path.join(unpacked_folder, f"userdata{i}")
            with open(file_path, "rb") as f:
                data = f.read()
                name=read_char_name(data)
                if name is None:
                    return
                
                char_name_list.append((name, file_path))
    
    elif MODE == 'PC':

        for i in range(10):

            file_path = os.path.join(unpacked_folder, f"USERDATA_0{i}")
            with open(file_path, "rb") as f:
                data = f.read()
                name=read_char_name(data)
                if name is None:
                    return
                
                char_name_list.append((name, file_path))


if __name__ == "__main__":

    load_file()

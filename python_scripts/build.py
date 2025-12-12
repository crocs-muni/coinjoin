import os
import datetime
import json
import re


def extract_month_year(folder_name):
    # Regex pattern to extract a date like "2022-06-01 00-00-00"
    date_pattern = re.compile(r'(\d{4})-(\d{2})-\d{2} \d{2}-\d{2}-\d{2}')

    match = date_pattern.search(folder_name)
    if match:
        year, month = match.group(1), match.group(2)
        month_name = datetime.datetime.strptime(month, "%m").strftime("%B")
        return f"{month_name} {year}"
    return None


class WebGenerator:

    def __init__(self, config):
        with open(config, "r") as file:
            structure = json.load(file)

        self.data_source = structure["data_source"]
        self.image_url = structure["image_url"]
        self.thumbnail_url = structure["thumbnail_url"]
        self.base = structure["web_base"]
        self.pages = structure["pages"]
        self.whitelist = structure["whitelist"]
        

    def is_whitelisted(self, name):
        for w in self.whitelist:
            if w == name[-len(w):]:
                return True
        return False


    def get_selector(self, coordinators, current, page):
        selector = "<div id='subnav'> <ul>"
        for coordinator in coordinators:
            selector += f"""<li><a href="{page}/{coordinator["dir"]}.html" class="{'current' if coordinator["dir"]==current else ""} {'active' if "active" in coordinator and coordinator["active"] == True else ""}" >{coordinator["name"]}</a></li>"""
        selector += "</div> </ul>"
        return selector

    def get_header(self, current_page, current_coordinator=None):
        if os.path.isfile(f"{self.data_source}/summary.json"):
            with open(f"{self.data_source}/summary.json", "r") as file:
                date = json.load(file)["date"]
        else:
            date = datetime.datetime.today().strftime('%d-%m-%Y')

        header = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>CoinJoin Statistics</title>
        <base href="{self.base}"/>
        <link rel="stylesheet" href="style.css?v2" />
        <link rel="icon" type="image/x-icon" href="favicon.ico">
        </head>
        <body>
            <p class=banner>This is a nightly build. If nightly is broken, visit a stable version: <a href=https://crocs-muni.github.io/coinjoin/stable/index.html>https://crocs-muni.github.io/coinjoin/stable/index.html</a></p>
            <header>
            <h1>CoinJoin Statistics</h1>
            <p class="update">Last updated: {date}</p>

            <nav class="menu">
            <ul>
        """
        for page,page_details in self.pages.items():
            if page == "joinmarket":
                continue
            page_dir = page
            if "coordinators" in page_details:
                page_dir += "/" + page_details["coordinators"][0]["dir"]
            header += f"""<li><a href="{page_dir}.html" class="{'current' if page==current_page else ""}  {'active' if "active" in page_details and page_details["active"] == True else ""}" >{page_details["name"]}</a></li>"""        
    
        header +=f"""
            </ul>
            </nav>
        {self.get_selector(self.pages[current_page]["coordinators"], current_coordinator, current_page) if "coordinators" in self.pages[current_page] else ""}
            </header>
        <img src="legend.png" alt="legend" id="legend" />
        <div id="containers">
        """
        if current_coordinator is None:
            if os.path.isfile(f"{self.data_source}/texts/{current_page}.html"):
                with open(f"{self.data_source}/texts/{current_page}.html", "r") as file:
                    text = file.read()
                    header += f"""<div class="container"><div class="text">{text}</div></div>"""
            else:
                print(f"{self.data_source}/texts/{current_page}.html", "Not found")
        else:
            if os.path.isfile(f'{self.data_source}/texts/{current_coordinator}.html'):
                with open(f'{self.data_source}/texts/{current_coordinator}.html', "r") as file:
                    print(f'{self.data_source}/texts/{current_coordinator}.html')
                    text = file.read()
                    header += f"""<div class="container"><div class="text">{text}</div></div>"""
            else:
                print(f'{self.data_source}/texts/{current_coordinator}.html', "Not found")

        return header

    @staticmethod
    def get_footer():
        return """
            </div>
            <div id="lightbox">
            <span class="close">&times;</span>
            <span class="arrow left">&#10094;</span>
            <img id="lightbox-img" src="" alt="">
            <span class="arrow right">&#10095;</span>
            </div>
            
            <script src="./js/lightbox.js?v1"></script>
        </body>
        </html>
        """

    def get_img_block(self, imgpath):
        return f"""   
            <div class="grid-item">
            <img src="{self.thumbnail_url}{imgpath}?v{datetime.datetime.today().strftime('%Y-%m-%d')}" 
                data-full="{self.image_url}{imgpath}?v{datetime.datetime.today().strftime('%Y-%m-%d')}" 
                alt="{imgpath}" loading="lazy" />
            </div>
    """

    def traverse_directories(self, root_dir, name_start):
        print(root_dir)
        base_depth = self.data_source.count(os.sep)
        output = ''
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames.sort(reverse=True)
            dir_name = os.path.basename(dirpath)
            
            depth = dirpath.count(os.sep) - base_depth
            if depth > 0:
                month_year = extract_month_year(dir_name)

                if month_year is not None:
                    output += f"    <h{depth + 1}>" + name_start + month_year + f"</h{depth + 1}>\n\n"
                else:
                    output += f"    <h{depth + 1}>" + name_start + dir_name + f"</h{depth + 1}>\n\n"
            
            if len(filenames) > 0:
                output += '    <div class="container">'

            for filename in filenames:
                if not self.is_whitelisted(filename):
                    continue
                filepath = os.path.join(dirpath, filename)
                imgpath = os.path.relpath(filepath, start=self.data_source)

                output += self.get_img_block(imgpath)
            
            if len(filenames) > 0:
                output += "    </div>\n"
        return output


    def get_large_images(self, images):
        result = ""
        for img in images:
            result += f"""<div class='container'> <div class='large'> 
            <img src="{self.image_url}{img}?v{datetime.datetime.today().strftime('%Y-%m-%d')}" 
                data-full="{self.thumbnail_url}{img}?v{datetime.datetime.today().strftime('%Y-%m-%d')}" 
                alt="{img}" loading="lazy" />
            </div> </div>\n"""
        
        return result
    

    def generate(self):

        for page,page_details in self.pages.items():
        
            if "coordinators" in page_details:
                os.makedirs(f"./{page}", exist_ok=True)
            
                for coordinator in page_details["coordinators"]:
                    start_directory = f'{self.data_source}{coordinator["dir"]}'

                    output = self.get_header(page, current_coordinator=coordinator["dir"])

                    if coordinator.get("large_images") is not None:
                        output += self.get_large_images(coordinator.get("large_images"))
                    
                    output += self.traverse_directories(start_directory, page_details["name"] + " - " + coordinator["name"] + " - ") 

                    if page == "wasabi2" and coordinator["dir"] == "wasabi2":
                        output += """
                        <h2>Flows</h2>
                        
                        <iframe src="./flows/coordinator_flows_counts_.html">
                            Your browser does not support iframes.
                        </iframe>
                        <iframe src="./flows/coordinator_flows_values_.html">
                            Your browser does not support iframes.
                        </iframe>
                        <iframe src="./flows/coordinator_flows_values_incl_zksnacks.html">
                            Your browser does not support iframes.
                        </iframe>
                    """

                    output += WebGenerator.get_footer()

                    with open(f'./{page}/{coordinator["dir"]}.html', "w") as file:
                        file.write(output)

        
            else:
                header = self.get_header(page)
                footer = WebGenerator.get_footer()

                if "paths" in self.pages[page]:
                    body = '<div class="container">'
                    for path in self.pages[page]["paths"]:
                        body += self.get_img_block(path)
                    body += "    </div>\n"
                
                else:
                    body = ""
                    if self.pages[page].get("large_images") is not None:
                        body += self.get_large_images(self.pages[page].get("large_images"))

                    start_directory = f'{self.data_source}{self.pages[page]["dir"]}' 
                    body += self.traverse_directories(start_directory, page_details["name"] + " - ") 

                output = header + body + footer

                with open(f"./{page}.html", "w") as file:
                    file.write(output)



if __name__ == "__main__":
    generator = WebGenerator("structure.json")
    generator.generate()

    

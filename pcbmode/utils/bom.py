#!/usr/bin/python

#import json
import os
import re
import pcbmode.config as config

from . import utils
from . import messages as msg
from .shape import Shape
from .style import Style



def make_bom(quantity=None):
    """
    
    """

    def natural_key(string_):
        """See http://www.codinghorror.com/blog/archives/001018.html"""
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

    def _getOutline():
        """
        Process the module's outline shape. Modules don't have to have an outline
        defined, so in that case return None.
        """
        shape = None

        outline_dict = config.brd.get('outline')
        if outline_dict != None:
            shape_dict = outline_dict.get('shape')
            if shape_dict != None:
                shape = Shape(shape_dict)
                style = Style(shape_dict, 'outline')
                shape.setStyle(style)

        return shape


     
    dnp_text = 'Do not populate'
    uncateg_text = 'Uncategorised'

    components_dict = config.brd['components']
    
    bom_dict = {}

    for refdef in components_dict:

        description = ''

        try:
            place = components_dict[refdef]['place']
        except:
            place = True

        try:
            ignore = components_dict[refdef]['bom']['ignore']
        except:
            ignore = False

        # If component isn't placed, ignore it
        if place == True and ignore == False:

            # Get footprint definition and shapes
            try:
                footprint_name = components_dict[refdef]['footprint']
            except:
                msg.error("Cannot find a 'footprint' name for refdef %s." % refdef)
            
            # Open footprint file
            fname = os.path.join(config.cfg['base-dir'],
                                 config.cfg['locations']['components'],
                                 footprint_name + '.json')
            footprint_dict = utils.dictFromJsonFile(fname)
 
            info_dict = footprint_dict.get('info') or {}
 
            try: 
                comp_bom_dict = components_dict[refdef]['bom']
            except:
                comp_bom_dict = {}
 
            try: 
                fp_bom_dict = footprint_dict['info']
            except:
                fp_bom_dict = {}
 
 
            # Override component BoM info on top of footprint info
            for key in comp_bom_dict:
                fp_bom_dict[key] = comp_bom_dict[key]

            description = fp_bom_dict.get('description') or uncateg_text

            try:
                dnp = components_dict[refdef]['bom']['dnp']
            except:
                dnp = False            

            if dnp == True:
                description = dnp_text
 
            if description not in bom_dict:
                bom_dict[description] = fp_bom_dict
                bom_dict[description]['refdefs'] = []
            bom_dict[description]['refdefs'].append(refdef)
    

    try:
        bom_content = config.brd['bom']
    except:
        bom_content = [
            {
              "field": "line-item",
              "text": "#"
            },
            {
              "field": "quantity",
              "text": "Qty"
            },
            {
              "field": "designators",
               "text": "Designators"
            }, 
            {
              "field": "description",
              "text": "Description"
            }, 
            {
              "field": "package",
              "text": "Package"
            }, 
            {
              "field": "manufacturer",
              "text": "Manufacturer"
            }, 
            {
              "field": "part-number",
              "text": "Part #"
            },
            {
              "field": "suppliers",
              "text": "Suppliers",
              "suppliers": 
              [
                {
                  "field": "farnell",
                  "text": "Farnell #",
                  "search-url": "http://uk.farnell.com/catalog/Search?st="
                },
                { 
                  "field": "mouser",
                  "text": "Mouser #",
                  "search-url": "http://uk.mouser.com/Search/Refine.aspx?Keyword="
                },
                { 
                  "field": "digikey",
                  "text": "Digi-Key #",
                  "search-url": "https://www.digikey.com/products/en?keywords="
                },
                {
                  "field": "octopart",
                  "text": "Octopart",
                  "search-url": "https://octopart.com/search?q="
                }
              ]
            },
            {
              "field": "notes",
              "text": "Notes"
            }
          ]



    # Set up the BoM file name
    bom_path = os.path.join(config.cfg['base-dir'],
                            config.cfg['locations']['build'],
                            'bom')
    # Create path if it doesn't exist already
    utils.create_dir(bom_path)

    board_name = config.cfg['name']
    board_revision = config.brd['config'].get('rev')
    base_name = "%s_rev_%s" % (board_name, board_revision)

    bom_html = os.path.join(bom_path, base_name + '_%s.html'% 'bom')
    bom_csv = os.path.join(bom_path, base_name + '_%s.csv'% 'bom')
    bom_xyrs = os.path.join(bom_path, base_name + '_%s.XYRS'% 'bom')


    html = []
    csv = []
    xyrs = []

    # Get the board's dimensions
    # This gives the bounding box of the shape
    outline = _getOutline()
    board_width = outline.getWidth()
    board_height = outline.getHeight()

    # To print as the file's header
    preamble = ('#This file was auto-generated by PCBmodE.\n#\n#The coordinates are relative to the bottom left of the board outline shape\n#\n#Rotation is in degrees, clock-wise, and as seen from the\n#top or EACH layer. Confirm with ASSEMBLY DRAWING for correctness.\n#\n#All dimension are in mils (.001").\n#')

    # XYRS header
    header = "#%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % ('Designator',
                                 'X-Loc',
                                 'Y-Loc',
                                 'Rotation',
                                 'Side',
                                 'solder-type',
                                 'x-size',
                                 'y-size',
                                 'value',
                                 'package',
                                 'populate',
                                 'part-number',
                                 'manufacturer')

    xyrs.append(preamble)
    xyrs.append(header)

    html.append('<html>')
    html.append('<style type="text/css">')
    try:
        css = config.stl['layout']['bom']['css']
    except:
        css = []
    for line in css:
        html.append(line)
    html.append('</style>')
    html.append('<table class="tg">')

    header = []
    for item in bom_content:
        if item['field'] == 'suppliers':
            for supplier in item['suppliers']:
                header.append("%s" % supplier['text'])
        else:
            header.append("%s" % item['text'])
            if item['field'] == 'quantity' and quantity != None:
                header.append("@%s" % quantity)

    html.append('  <tr>')
    html.append('    <th class="tg-title" colspan="%s">Bill of materials -- %s rev %s</th>' % (len(header), board_name, board_revision))
    html.append('  </tr>') 
    html.append('  <tr>')
    for item in header:
        if item == 'Designators':
            html.append('    <th class="tg-header-des">%s</th>' % item)
        else:
            html.append('    <th class="tg-header">%s</th>' % item)
    html.append('  </tr>')
    
    uncateg_content = []
    dnp_content = []
    index = 1

    for desc in sorted(bom_dict):
        for refdef in bom_dict[desc]['refdefs']:
            ent = components_dict[refdef]
            try:
                dnp = components_dict[refdef]['bom']['dnp']
            except:
                dnp = False            
            xyrs.append("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (refdef,
                                          (board_width/2 + ent['location'][0]) * 39.37,
                                          (board_height/2 + ent['location'][1]) * 39.37,
                                          ent['rotate'],
                                          ent['layer'],
                                          bom_dict[desc].get('solder-type', 'SMD'),
                                          float(bom_dict[desc].get('x-size', 0.0)) * 39.37,
                                          float(bom_dict[desc].get('y-size', 0.0)) * 39.37,
                                          bom_dict[desc].get('value', ''),
                                          bom_dict[desc].get('package', ''),
                                          '0' if dnp == True else '1',
                                          bom_dict[desc].get('part-number', ''),
                                          bom_dict[desc].get('manufacturer', '')))

        content = []
        for item in bom_content:
            if item['field'] == 'line-item':
                content.append("<strong>%s</strong>" % str(index))
            elif item['field'] == 'suppliers':
                for supplier in item['suppliers']:

                    try:
                        number = bom_dict[desc][item['field']][supplier['field']]
                    except:
                        number = ""

                    search_url = supplier.get('search-url')
                    if search_url != None:
                        content.append('<a href="%s%s">%s</a>' % (search_url, number, number))
                    else:
                        content.append(number)

            elif item['field'] == 'quantity':
                units = len(bom_dict[desc]['refdefs'])
                content.append("%s" % (str(units)))
                if quantity != None:
                    content.append("%s" % (str(units*int(quantity))))
            elif item['field'] == 'designators':
                # Natural/human sort the list of designators
                sorted_list = sorted(bom_dict[desc]['refdefs'], key=natural_key)

                refdefs = ''
                for refdef in sorted_list[:-1]:
                    refdefs += "%s " % refdef
                refdefs += "%s" % sorted_list[-1]
                content.append("%s " % refdefs)
            elif item['field'] == 'description':
                content.append("%s " % desc)
            elif item['field'] == 'part-number':
                try:
                    number = bom_dict[desc][item['field']]
                except:
                    number = ""
                content.append('<span style="white-space:nowrap">%s</span>' % number)
            else:
                try:
                    content.append(bom_dict[desc][item['field']])
                except:
                    content.append("")

        if desc == uncateg_text:
            uncateg_content = content
        elif desc == dnp_text:
            dnp_content = content
        else:
            html.append('  <tr>')
            for item in content:
                html.append('    <td class="tg-item-%s">%s</td>' % (('odd','even')[index%2==0], item))
            html.append('  </tr>')
            index += 1


    for content in (dnp_content, uncateg_content):
        html.append('  <tr class="tg-skip">')
        html.append('  </tr>')        
        html.append('  <tr>')
        if len(content) > 0:
            content[0] = index
        for item in content:
            html.append('    <td class="tg-item-%s">%s</td>' % (('odd','even')[index%2==0], item))
        html.append('  </tr>')
        index += 1


    html.append('</table>')

    html.append('<p>Generated by <a href="http://pcbmode.com">PCBmodE</a>, maintained by <a href="http://boldport.com">Boldport</a>.')

    html.append('</html>')

    with open(bom_html, "wb") as f:
        for line in html:
            f.write(line+'\n')

    with open(bom_xyrs, "wb") as f:
        for line in xyrs:
            f.write(line+'\n')

    
    #print bom_dict



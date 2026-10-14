"""Reuse packaged Feather geometry without separate icon requests or HTML parsing."""
import json
from pathlib import Path
from xml.etree import ElementTree
from .friday_assets import ICONS

SHAPE_TAGS = frozenset({'path','line','polyline','polygon','rect','circle','ellipse'})
SHAPE_ATTRIBUTES = frozenset({'d','points','x','y','x1','x2','y1','y2','width','height','rx','ry','cx','cy','r'})


def packaged_icon_shapes():
    shapes={}
    for name in sorted(ICONS):
        root=ElementTree.parse(Path(__file__).parent/'assets'/('friday-icon-'+name+'.svg')).getroot()
        items=[]
        for child in root:
            tag=child.tag.rsplit('}',1)[-1]
            if tag not in SHAPE_TAGS or not set(child.attrib)<=SHAPE_ATTRIBUTES:
                raise ValueError('Unsupported packaged icon geometry')
            items.append({'tag':tag,'attributes':dict(child.attrib)})
        shapes[name]=items
    return shapes


INLINE_ICON_CSS = 'svg.everyday-icon,svg.everyday-arrow{color:#000;flex:none}'
INLINE_ICON_JS = ('const fridayInlineIcons=Object.freeze('+json.dumps(packaged_icon_shapes())+');\n')

INLINE_ICON_JS += r"""
      function fridayInlineIcon(name,className){
        const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
        svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('width','22');svg.setAttribute('height','22');
        svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','2');
        svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');
        svg.setAttribute('class',className);svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');
        for(const shape of fridayInlineIcons[name]||fridayInlineIcons.shield){
          const node=document.createElementNS(svg.namespaceURI,shape.tag);
          for(const [key,value] of Object.entries(shape.attributes))node.setAttribute(key,value);
          svg.append(node);
        }
        return svg;
      }
"""

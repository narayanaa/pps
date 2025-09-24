# Parser module - psense namespace
# Make imports conditional to handle missing dependencies
try:
    from . import pdf
except ImportError:
    pdf = None
    
try:
    from . import docx
except ImportError:
    docx = None
    
try:
    from . import ebook
except ImportError:
    ebook = None
    
try:
    from . import md
except ImportError:
    md = None
    
try:
    from . import yaml
except ImportError:
    yaml = None
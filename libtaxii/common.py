"""
Common utility classes and functions used throughout libtaxii.

"""

from operator import attrgetter
from StringIO import StringIO

import dateutil.parser
from lxml import etree

_XML_PARSER = None


def get_xml_parser():
    """Return the XML parser currently in use.

    If one has not already been set (via :py:func:`set_xml_parser()`), a new
    ``etree.XMLParser`` is constructed with ``no_network=True`` and
    ``huge_tree=True``.
    """
    global _XML_PARSER
    if _XML_PARSER is None:
        _XML_PARSER = etree.XMLParser(no_network=True, huge_tree=True)
    return _XML_PARSER


def set_xml_parser(xml_parser=None):
    """Set the libtaxii.messages XML parser.

    Args:
        xml_parser (etree.XMLParser): The parser to use to parse TAXII XML.
    """
    global _XML_PARSER
    _XML_PARSER = xml_parser


def parse_datetime_string(datetime_string):
    """Parse a string into a :py:class:`datetime.datetime`.

    libtaxii users should not need to use this function directly.
    """
    if not datetime_string:
        return None
    return dateutil.parser.parse(datetime_string)


class TAXIIBase(object):
    """
    Base class for all TAXII Messages and Message component types.

    libtaxii users should not need to use this class directly.
    """

    @property
    def sort_key(self):
        """
        This property allows list of TAXII objects to be compared efficiently.
        The __eq__ method uses this property to sort the lists before
        comparisons are made.

        Subclasses must implement this property.
        """
        raise NotImplementedError()

    def to_etree(self):
        """Create an etree representation of this class.

        Subclasses must implement this method.
        """
        raise NotImplementedError()

    def to_dict(self):
        """Create a dictionary representation of this class.

        Subclasses must implement this method.
        """
        raise NotImplementedError()

    def to_xml(self, pretty_print=False):
        """Create an XML representation of this class.

        Subclasses should not need to implement this method.
        """
        return etree.tostring(self.to_etree(), pretty_print=pretty_print)

    def to_text(self, line_prepend=''):
        """Create a nice looking (this is a subjective term!)
        textual representation of this class. Subclasses should 
        implement this method.
        
        Note that this is just a convenience method for making
        TAXII Messages nice to read for humans and may change
        drastically in future versions of libtaxii.
        """
        raise NotImplementedError()

    @classmethod
    def from_etree(cls, src_etree):
        """Create an instance of this class from an etree.

        Subclasses must implement this method.
        """
        raise NotImplementedError()

    @classmethod
    def from_dict(cls, d):
        """Create an instance of this class from a dictionary.

        Subclasses must implement this method.
        """
        raise NotImplementedError()

    @classmethod
    def from_xml(cls, xml):
        """Create an instance of this class from XML.

        Subclasses should not need to implement this method.
        """
        if isinstance(xml, basestring):
            xmlstr = StringIO(xml)
        else:
            xmlstr = xml

        etree_xml = etree.parse(xmlstr, get_xml_parser()).getroot()
        return cls.from_etree(etree_xml)

    # Just noting that there is not a from_text() method. I also 
    # don't think there will ever be one.

    def __eq__(self, other, debug=False):
        """
        Generic method used to check equality of objects of any TAXII type.

        Also allows for ``print``-based debugging output showing differences.

        In order for subclasses to use this function, they must meet the
        following criteria:
        1. All class properties start with one underscore.
        2. The sort_key property is implemented.

        Args:
            self (object): this object
            other (object): the object to compare ``self`` against.
            debug (bool): Whether or not to print debug statements as the
                equality comparison is performed.
        """
        if other is None:
            if debug:
                print 'other was None!'
            return False

        if self.__class__.__name__ != other.__class__.__name__:
            if debug:
                print 'class names not equal: %s != %s' % (self.__class__.__name__, other.__class__.__name__)
            return False

        # Get all member properties that start with '_'
        members = [attr for attr in dir(self) if not callable(attr) and attr.startswith('_') and not attr.startswith('__')]
        for member in members:
            # TODO: The attr for attr... statement includes functions for some strange reason...
            if member not in self.__dict__:
                continue

            if debug:
                print 'member name: %s' % member
            self_value = self.__dict__[member]
            other_value = other.__dict__[member]

            if isinstance(self_value, TAXIIBase):
                # A debuggable equals comparison can be made
                eq = self_value.__eq__(other_value, debug)
            elif isinstance(self_value, list):
                # We have lists to compare
                if len(self_value) != len(other_value):
                    # Lengths not equal
                    member = member + ' lengths'
                    self_value = len(self_value)
                    other_value = len(other_value)
                    eq = False
                elif len(self_value) == 0:
                    # Both lists are of size 0, and therefore equal
                    eq = True
                else:
                    # Equal sized, non-0 length lists. The list might contain
                    # TAXIIBase objects, or it might not. Peek at the first
                    # item to see whether it is a TAXIIBase object or not.
                    if isinstance(self_value[0], TAXIIBase):
                        # All TAXIIBase objects have the 'sort_key' property implemented
                        self_value = sorted(self_value, key=attrgetter('sort_key'))
                        other_value = sorted(other_value, key=attrgetter('sort_key'))
                        for self_item, other_item in zip(self_value, other_value):
                            # Compare the ordered lists element by element
                            eq = self_item.__eq__(other_item, debug)
                    else:
                        # Assume they don't... just do a set comparison
                        eq = set(self_value) == set(other_value)
            elif isinstance(self_value, dict):
                # Dictionary to compare
                if len(set(self_value.keys()) - set(other_value.keys())) != 0:
                    if debug:
                        print 'dict keys not equal: %s != %s' % (self_value, other_value)
                    eq = False
                for k, v in self_value.iteritems():
                    if other_value[k] != v:
                        if debug:
                            print 'dict values not equal: %s != %s' % (v, other_value[k])
                        eq = False
                eq = True
            elif isinstance(self_value, etree._Element):
                # Non-TAXII etree element (i.e. STIX)
                eq = (etree.tostring(self_value) == etree.tostring(other_value))
            else:
                # Do a direct comparison
                eq = (self_value == other_value)

            # TODO: is this duplicate?
            if not eq:
                if debug:
                    print '%s was not equal: %s != %s' % (member, self_value, other_value)
                return False

        return True

    def __ne__(self, other, debug=False):
        return not self.__eq__(other, debug)

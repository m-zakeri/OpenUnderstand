package org.apache.xerces.xni;
public class XMLString {
    public char[] ch;

    /** The offset into the character array. */
    public int offset;

    /** The length of characters from the offset. */
    public int length;

    //
    // Constructors
    //

    /** Default constructor. */
    public XMLString() {
    } // <init>()

    /**
     * Constructs an XMLString structure preset with the specified
     * values.
     * 
     * @param ch     The character array.
     * @param offset The offset into the character array.
     * @param length The length of characters from the offset.
     */
    public XMLString(char[] ch, int offset, int length) {
        setValues(ch, offset, length);
    } // <init>(char[],int,int)

    /**
     * Constructs an XMLString structure with copies of the values in
     * the given structure.
     * <p>
     * <strong>Note:</strong> This does not copy the character array;
     * only the reference to the array is copied.
     *
     * @param string The XMLString to copy.
     */
    public XMLString(XMLString string) {
        setValues(string);
    } // <init>(XMLString)

    //
    // Public methods
    //

    /**
     * Initializes the contents of the XMLString structure with the
     * specified values.
     * 
     * @param ch     The character array.
     * @param offset The offset into the character array.
     * @param length The length of characters from the offset.
     */
    public void setValues(char[] ch, int offset, int length) {
        this.ch = ch;
        this.offset = offset;
        this.length = length;
    } // setValues(char[],int,int)

    /**
     * Initializes the contents of the XMLString structure with copies
     * of the given string structure.
     * <p>
     * <strong>Note:</strong> This does not copy the character array;
     * only the reference to the array is copied.
     * 
     * @param s
     */
    public void setValues(XMLString s) {
        setValues(s.ch, s.offset, s.length);
    } // setValues(XMLString)

    /** Resets all of the values to their defaults. */
    public void clear() {
        this.ch = null;
        this.offset = 0;
        this.length = -1;
    } // clear()

    /**
     * Returns true if the contents of this XMLString structure and
     * the specified array are equal.
     * 
     * @param ch     The character array.
     * @param offset The offset into the character array.
     * @param length The length of characters from the offset.
     */
    public boolean equals(char[] ch, int offset, int length) {
        if (ch == null) {
            return false;
        }
        if (this.length != length) {
            return false;
        }

        for (int i=0; i<length; i++) {
            if (this.ch[this.offset+i] != ch[offset+i] ) {
                return false;
            }
        }
        return true;
    } // equals(char[],int,int):boolean

    /**
     * Returns true if the contents of this XMLString structure and
     * the specified string are equal.
     * 
     * @param s The string to compare.
     */
    public boolean equals(String s) {
        if (s == null) {
            return false;
        }
        if ( length != s.length() ) {
            return false;
        }

        // is this faster than call s.toCharArray first and compare the 
        // two arrays directly, which will possibly involve creating a
        // new char array object.
        for (int i=0; i<length; i++) {
            if (ch[offset+i] != s.charAt(i)) {
                return false;
            }
        }

        return true;
    } // equals(String):boolean

    //
    // Object methods
    //

    /** Returns a string representation of this object. */
    public String toString() {
        return length > 0 ? new String(ch, offset, length) : "";
    } // toString():String

} // class XMLString

===================================================
G-Code Transformation Tool (gcode-transform.py)
===================================================

This Python 3 script provides a robust, low-level tool for performing geometric
transformations—specifically **rotation (along the Z-axis)** and **translation (X/Y shifting)**—on pre-sliced G-Code files.

It uses NumPy for matrix mathematics to correctly handle **rotation around an arbitrary center point** and precisely tracks G-Code state (Absolute ``G90``/Relative ``G91`` modes) for reliable output.

***

Dependencies and Installation
=============================

The script requires **Python 3** and the scientific computing library **NumPy**.

Debian/Ubuntu Systems
---------------------

Install the required dependencies by running:

::

    sudo apt-get install python3 python3-numpy

Other Systems (using pip)
-------------------------

Install NumPy using pip:

::

    pip install numpy

***

Usage
=====

Run the script using the ``python3`` interpreter, piping the output (``>``) to a new G-Code file. All transformation parameters are **optional** and default to zero (0).

Basic Syntax
------------

::

    python3 gcode-transform.py [OPTIONS] input.gcode > output.gcode

Basic Example
-------------

This command rotates the ``input.gcode`` file **90 degrees clockwise** around the default center point (``125x100``) and saves the result to ``output.gcode``.

::

    python3 gcode-transform.py --rotate 90 input.gcode > output.gcode

***

Parameters and Defaults
=======================

The table below outlines the interpretation for positive and negative values.

.. list-table::
   :widths: 15 15 70
   :header-rows: 1

   * - Parameter
     - Value / Default
     - Interpretation & Effect
   * - ``--shiftx``
     - ``5`` / **Default: 0.0**
     - Shifts in the **Positive X** (Right) / **Negative X** (Left) direction.
   * - ``--shifty``
     - ``5`` / **Default: 0.0**
     - Shifts in the **Positive Y** (Forward) / **Negative Y** (Backward) direction.
   * - ``--rotate``
     - ``4`` / **Default: 0.0**
     - Rotation in the **Clockwise (CW)** / **Counter-Clockwise (CCW)** direction.
   * - ``--center``
     - ``XxY`` (e.g., ``110x110``) / **Default: 125x100**
     - Specifies the coordinate point around which rotation occurs. The default is suitable for Prusa i3-style 250x200 mm beds.
   * - ``--precision``
     - Integer (e.g., ``3``) / **Default: 3**
     - Sets the decimal places for output coordinates.

Full Transformation Example
---------------------------

This command applies a **4° counter-clockwise rotation** (``-4``) and shifts the print **5 mm to the left** (``-5``) and **10 mm forward** (``10``).

::

    python3 gcode-transform.py --rotate -4 --shiftx -5 --shifty 10 --center 110x110 input.gcode > transformed.gcode

Shift-Only Example
------------------

If rotation is omitted, only the translation (shifting) occurs.

::

    python3 gcode-transform.py --shiftx 5 --shifty -2.5 input.gcode > shifted_only.gcode

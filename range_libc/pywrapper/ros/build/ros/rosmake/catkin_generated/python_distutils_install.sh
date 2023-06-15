#!/bin/sh

if [ -n "$DESTDIR" ] ; then
    case $DESTDIR in
        /*) # ok
            ;;
        *)
            /bin/echo "DESTDIR argument must be absolute... "
            /bin/echo "otherwise python's distutils will bork things."
            exit 1
    esac
fi

echo_and_run() { echo "+ $@" ; "$@" ; }

echo_and_run cd "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros/rosmake"

# ensure that Python install destination exists
echo_and_run mkdir -p "$DESTDIR/usr/local/lib/python3.11/site-packages"

# Note that PYTHONPATH is pulled from the environment to support installing
# into one location when some dependencies were installed in another
# location, #123.
echo_and_run /usr/bin/env \
    PYTHONPATH="/usr/local/lib/python3.11/site-packages:/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/lib/python3.11/site-packages:$PYTHONPATH" \
    CATKIN_BINARY_DIR="/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build" \
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/venv/bin/python" \
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros/rosmake/setup.py" \
    egg_info --egg-base /Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros/rosmake \
    build --build-base "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros/rosmake" \
    install \
    --root="${DESTDIR-/}" \
     --prefix="/usr/local" --install-scripts="/usr/local/bin"

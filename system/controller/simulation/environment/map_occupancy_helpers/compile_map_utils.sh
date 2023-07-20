g++ -O3 -Wall -fPIC -shared -std=c++11 \
    map_utils.cpp \
    -o map_utils_cpp.dylib \
    -static-libstdc++ \
    -undefined dynamic_lookup \
    -Wl,-rpath,"\$ORIGIN" \
    $(python3 -m pybind11 --includes) \
    $@
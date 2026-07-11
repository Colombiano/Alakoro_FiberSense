#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/eigen.h>
#include <pybind11/functional.h>

namespace py = pybind11;

// Forward declarations
void init_signal_processor(py::module& m);
void init_das_decoder(py::module& m);
void init_event_detector(py::module& m);

PYBIND11_MODULE(alakoro, m) {
    m.doc() = "Alakoro_FiberSense - C++ core bindings for DAS processing";
    
    m.attr("__version__") = "1.0.0";
    m.attr("__author__") = "Luiz Paulo Colombiano";
    
    init_signal_processor(m);
    init_das_decoder(m);
    init_event_detector(m);
}

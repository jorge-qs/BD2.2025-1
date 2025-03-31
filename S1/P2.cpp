#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstdio>

// Estructura MetadataEntry (sin pragma pack)
struct MetadataEntry {
    long long pos;  // 8 bytes: posición inicial en el archivo de datos
    int size;       // 4 bytes: tamaño en bytes del registro almacenado
    char active;    // 1 byte: '1' = activo, '0' = eliminado
};

// Función para escribir una entrada de metadata (serialización manual)
void writeMetadataEntry(std::ostream &os, const MetadataEntry &entry) {
    os.write(reinterpret_cast<const char*>(&entry.pos), sizeof(entry.pos));
    os.write(reinterpret_cast<const char*>(&entry.size), sizeof(entry.size));
    os.write(&entry.active, sizeof(entry.active));
}

// Función para leer una entrada de metadata (deserialización manual)
bool readMetadataEntry(std::istream &is, MetadataEntry &entry) {
    if (!is.read(reinterpret_cast<char*>(&entry.pos), sizeof(entry.pos)))
        return false;
    if (!is.read(reinterpret_cast<char*>(&entry.size), sizeof(entry.size)))
        return false;
    if (!is.read(&entry.active, sizeof(entry.active)))
        return false;
    return true;
}

// Registro Matricula de longitud variable
struct Matricula {
    std::string codigo;
    int ciclo;
    double mensualidad;
    std::string observaciones;
};

// Clase que gestiona el archivo de datos y el archivo de metadata
class VariableRecordManager {
private:
    std::string dataFilename;
    std::string metaFilename;

    // Escribe un registro en el archivo de datos y retorna la MetadataEntry asociada.
    MetadataEntry writeRecord(const Matricula &mat) {
        std::ofstream dataOut(dataFilename, std::ios::binary | std::ios::app);
        dataOut.seekp(0, std::ios::end);
        long long pos = dataOut.tellp();

        // Se escribe el registro de la siguiente forma:
        // 1. Código: primero se escribe la longitud y luego la cadena.
        int lenCodigo = mat.codigo.size();
        dataOut.write(reinterpret_cast<const char*>(&lenCodigo), sizeof(int));
        dataOut.write(mat.codigo.data(), lenCodigo);
        // 2. Ciclo
        dataOut.write(reinterpret_cast<const char*>(&mat.ciclo), sizeof(int));
        // 3. Mensualidad
        dataOut.write(reinterpret_cast<const char*>(&mat.mensualidad), sizeof(double));
        // 4. Observaciones: se escribe la longitud y luego la cadena.
        int lenObs = mat.observaciones.size();
        dataOut.write(reinterpret_cast<const char*>(&lenObs), sizeof(int));
        dataOut.write(mat.observaciones.data(), lenObs);

        dataOut.flush();
        long long endPos = dataOut.tellp();
        dataOut.close();

        MetadataEntry entry;
        entry.pos = pos;
        entry.size = static_cast<int>(endPos - pos);
        entry.active = '1';  // Registro activo
        return entry;
    }

    // Lee un registro Matricula del archivo de datos usando la MetadataEntry.
    Matricula readRecordFromData(const MetadataEntry &entry) {
        Matricula mat;
        std::ifstream dataIn(dataFilename, std::ios::binary);
        dataIn.seekg(entry.pos);

        // Leer "codigo"
        int lenCodigo;
        dataIn.read(reinterpret_cast<char*>(&lenCodigo), sizeof(int));
        char *bufferCodigo = new char[lenCodigo];
        dataIn.read(bufferCodigo, lenCodigo);
        mat.codigo = std::string(bufferCodigo, lenCodigo);
        delete[] bufferCodigo;

        // Leer "ciclo" y "mensualidad"
        dataIn.read(reinterpret_cast<char*>(&mat.ciclo), sizeof(int));
        dataIn.read(reinterpret_cast<char*>(&mat.mensualidad), sizeof(double));

        // Leer "observaciones"
        int lenObs;
        dataIn.read(reinterpret_cast<char*>(&lenObs), sizeof(int));
        char *bufferObs = new char[lenObs];
        dataIn.read(bufferObs, lenObs);
        mat.observaciones = std::string(bufferObs, lenObs);
        delete[] bufferObs;

        dataIn.close();
        return mat;
    }

public:
    VariableRecordManager(const std::string &dataFile, const std::string &metaFile)
            : dataFilename(dataFile), metaFilename(metaFile) {
        // Crear los archivos si no existen.
        std::ofstream dataOut(dataFilename, std::ios::binary | std::ios::app);
        dataOut.close();
        std::ofstream metaOut(metaFilename, std::ios::binary | std::ios::app);
        metaOut.close();
    }

    // Agrega un registro al final (O(1)) y actualiza la metadata.
    void add(const Matricula &mat) {
        MetadataEntry entry = writeRecord(mat);
        std::ofstream metaOut(metaFilename, std::ios::binary | std::ios::app);
        writeMetadataEntry(metaOut, entry);
        metaOut.close();
    }

    // Devuelve todos los registros activos.
    std::vector<Matricula> load() {
        std::vector<Matricula> records;
        std::ifstream metaIn(metaFilename, std::ios::binary);
        MetadataEntry entry;
        while (readMetadataEntry(metaIn, entry)) {
            if (entry.active == '1') {  // Sólo se consideran registros activos.
                Matricula mat = readRecordFromData(entry);
                records.push_back(mat);
            }
        }
        metaIn.close();
        return records;
    }

    // Lee el registro en la posición "index" (basado en el orden de inserción) en O(1).
    // Retorna true si se pudo leer el registro (almacenándolo en "mat"), false en caso contrario.
    bool readRecord(int index, Matricula &mat) {
        // Cada entrada de metadata tiene un tamaño fijo de 13 bytes (8+4+1).
        const int entrySize = 13;
        std::ifstream metaIn(metaFilename, std::ios::binary);
        metaIn.seekg(index * entrySize);
        MetadataEntry entry;
        if (!readMetadataEntry(metaIn, entry)) {
            metaIn.close();
            return false;
        }
        metaIn.close();
        if (entry.active != '1')
            return false;
        mat = readRecordFromData(entry);
        return true;
    }

    // Elimina el registro en la posición "index" marcándolo como eliminado en la metadata (O(1)).
    bool remove(int index) {
        const int entrySize = 13;
        std::fstream metaIO(metaFilename, std::ios::binary | std::ios::in | std::ios::out);
        metaIO.seekg(index * entrySize);
        MetadataEntry entry;
        if (!readMetadataEntry(metaIO, entry)) {
            metaIO.close();
            return false;
        }
        if (entry.active != '1') {
            metaIO.close();
            return false;
        }
        // Marcar el registro como eliminado.
        entry.active = '0';
        metaIO.seekp(index * entrySize);
        writeMetadataEntry(metaIO, entry);
        metaIO.close();
        return true;
    }
};

int main() {
    std::string dataFile = "matricula_data.dat";
    std::string metaFile = "matricula_meta.dat";

    std::remove(dataFile.c_str());
    std::remove(metaFile.c_str());

    VariableRecordManager vrm(dataFile, metaFile);

    // Prueba 1: Agregar registros
    std::cout << "=== Prueba 1: Agregar registros ===" << std::endl;
    Matricula m1 = {"C001", 1, 1000.50, "Primera matricula"};
    Matricula m2 = {"C002", 2, 1500.75, "Segunda matricula con observaciones"};
    Matricula m3 = {"C003", 3, 2000.00, "Tercera matricula"};
    vrm.add(m1);
    vrm.add(m2);
    vrm.add(m3);
    std::cout << "Se agregaron 3 registros." << std::endl;

    // Prueba 2: Cargar todos los registros
    std::cout << "\n=== Prueba 2: Cargar registros ===" << std::endl;
    std::vector<Matricula> records = vrm.load();
    for (size_t i = 0; i < records.size(); i++) {
        std::cout << "Registro " << i << ": "
                  << records[i].codigo << ", "
                  << records[i].ciclo << ", "
                  << records[i].mensualidad << ", "
                  << records[i].observaciones << std::endl;
    }

    // Prueba 3: Leer registro específico (posición 1)
    std::cout << "\n=== Prueba 3: Leer registro en posicion 1 ===" << std::endl;
    Matricula readMat;
    if (vrm.readRecord(1, readMat)) {
        std::cout << "Registro 1: "
                  << readMat.codigo << ", "
                  << readMat.ciclo << ", "
                  << readMat.mensualidad << ", "
                  << readMat.observaciones << std::endl;
    } else {
        std::cout << "No se pudo leer el registro en la posicion 1." << std::endl;
    }

    // Prueba 4: Eliminar registro (posición 1)
    std::cout << "\n=== Prueba 4: Eliminar registro en posicion 1 ===" << std::endl;
    if (vrm.remove(1)) {
        std::cout << "Registro en la posicion 1 eliminado exitosamente." << std::endl;
    } else {
        std::cout << "Error al eliminar el registro en la posicion 1." << std::endl;
    }

    // Prueba 5: Cargar registros después de la eliminación
    std::cout << "\n=== Prueba 5: Cargar registros despuos de la eliminacion ===" << std::endl;
    records = vrm.load();
    for (size_t i = 0; i < records.size(); i++) {
        std::cout << "Registro " << i << ": "
                  << records[i].codigo << ", "
                  << records[i].ciclo << ", "
                  << records[i].mensualidad << ", "
                  << records[i].observaciones << std::endl;
    }

    // Prueba 6: Intentar leer el registro eliminado (posición 1)
    std::cout << "\n=== Prueba 6: Intentar leer registro eliminado en posicion 1 ===" << std::endl;
    if (vrm.readRecord(1, readMat)) {
        std::cout << "Registro 1: "
                  << readMat.codigo << ", "
                  << readMat.ciclo << ", "
                  << readMat.mensualidad << ", "
                  << readMat.observaciones << std::endl;
    } else {
        std::cout << "El registro en la posicion 1 ha sido eliminado o no existe." << std::endl;
    }

    return 0;
}

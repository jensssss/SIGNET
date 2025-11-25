// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Import library Ownable dari OpenZeppelin
// Kontrak ini memerlukan instalasi @openzeppelin/contracts
import "@openzeppelin/contracts/access/Ownable.sol"; 

contract SignetRegistry is Ownable {
    
    // --- STRUKTUR DATA (Direct Storage) ---
    
    // Structure untuk menyimpan metadata dan info publisher
    struct Content {
        address publisher;
        string title;
        string description;
        uint256 timestamp;
    }
    
    // Database utama: pHash Video -> Data Content
    mapping(string => Content) public contentRegistry;
    
    // Mapping untuk Whitelist Publisher (True = Boleh Upload/Bayar Langganan)
    mapping(address => bool) public authorizedPublishers;

    // Array untuk memudahkan Backend Python mengambil semua Hash (Looping Search)
    string[] public allHashes;

    // Events untuk notifikasi Off-chain
    event PublisherAdded(address indexed clientAddress);
    event ContentRegistered(string indexed pHash, address indexed publisher);
    
    // --- FIX ERROR Ownable Constructor ---
    // Meneruskan alamat deployer (msg.sender) sebagai pemilik awal kontrak.
    constructor() Ownable(msg.sender) {
        // Otomatis menetapkan wallet yang deploy sebagai Admin (Owner).
    }
    
    // --- MODIFIER (RBAC) ---
    
    // Hanya wallet yang terdaftar di Whitelist yang bisa memanggil fungsi Write
    modifier onlyPublisher() {
        // Kontrak Ownable memberikan hak 'Owner' (Admin) untuk memanggil semua fungsi, 
        // tapi kita batasi Publisher biasa yang sudah di-whitelist.
        require(authorizedPublishers[msg.sender] == true, "SIGNET: Not an authorized publisher.");
        _;
    }

    // --- FUNGSI ADMIN (onlyOwner) ---
    
    // Fungsi untuk mendaftarkan Client baru (Scene 0)
    // HANYA bisa dipanggil oleh wallet Admin/Deployer.
    function addPublisher(address _clientWallet) external onlyOwner {
        require(_clientWallet != address(0), "SIGNET: Invalid address.");
        require(authorizedPublishers[_clientWallet] == false, "SIGNET: Client already registered.");
        
        authorizedPublishers[_clientWallet] = true;
        emit PublisherAdded(_clientWallet); 
    }

    // --- FUNGSI PUBLISHER (WRITE/Bayar Gas) ---
    
    // Fungsi untuk mendaftarkan Hash Konten (Scene 1)
    function registerContent(
        string memory _pHash, 
        string memory _title, 
        string memory _desc
    ) external onlyPublisher {
        
        require(bytes(_pHash).length > 0, "SIGNET: Hash cannot be empty.");
        // Mencegah Hash yang sama di-register 2x
        require(contentRegistry[_pHash].publisher == address(0), "SIGNET: Hash already registered."); 

        // Simpan data di mapping
        contentRegistry[_pHash] = Content({
            publisher: msg.sender,
            title: _title,
            description: _desc,
            timestamp: block.timestamp
        });

        // Tambahkan hash ke array list agar mudah dibaca Backend (getAllHashes)
        allHashes.push(_pHash);
        
        emit ContentRegistered(_pHash, msg.sender);
    }

    // --- FUNGSI PUBLIC (READ/GRATIS) ---

    // Fungsi KUNCI untuk Backend Python mencari semua hash (Scene 2)
    // Mengembalikan list semua hash yang terdaftar (untuk Nearest Neighbor Search)
    function getAllHashes() public view returns (string[] memory) {
        return allHashes;
    }
    
    // Fungsi untuk mengambil detail data sebuah hash
    function getContentData(string memory _pHash) public view returns (
        address publisher, 
        string memory title, 
        string memory description, 
        uint256 timestamp
    ) {
        Content storage content = contentRegistry[_pHash];
        // Cek apakah hash terdaftar
        require(content.publisher != address(0), "SIGNET: Content not found.");

        return (
            content.publisher,
            content.title,
            content.description,
            content.timestamp
        );
    }
}